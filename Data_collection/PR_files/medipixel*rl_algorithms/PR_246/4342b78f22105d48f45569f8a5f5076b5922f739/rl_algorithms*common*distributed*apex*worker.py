import argparse
from collections import deque
from typing import Dict

import numpy as np
import pyarrow as pa
import ray
import zmq

from rl_algorithms.common.distributed.abstract.worker import (
    DistributedWorkerWrapper,
    Worker,
)
from rl_algorithms.utils.config import ConfigDict


@ray.remote(num_cpus=1)
class ApeXWorkerWrapper(DistributedWorkerWrapper):
    """Wrapper class for ApeX based distributed workers

    Attributes:
        hyper_params (ConfigDict): worker hyper_params
        update_step (int): tracker for learner update step
        use_n_step (int): indication for using n-step transitions
        sub_socket (zmq.Context): subscriber socket for receiving params from learner
        push_socket (zmq.Context): push socket for sending experience to global buffer

    """

    def __init__(self, worker: Worker, args: argparse.Namespace, comm_cfg: ConfigDict):
        DistributedWorkerWrapper.__init__(self, worker, args, comm_cfg)
        self.update_step = 0
        self.hyper_params = self.worker.hyper_params
        self.use_n_step = self.hyper_params.n_step > 1

        self.worker._init_env()

    # pylint: disable=attribute-defined-outside-init
    def init_communication(self):
        """Initialize sockets connecting worker-learner, worker-buffer"""
        # for receiving params from learner
        ctx = zmq.Context()
        self.sub_socket = ctx.socket(zmq.SUB)
        self.sub_socket.setsockopt_string(zmq.SUBSCRIBE, "")
        self.sub_socket.setsockopt(zmq.CONFLATE, 1)
        self.sub_socket.connect(f"tcp://127.0.0.1:{self.comm_cfg.learner_worker_port}")

        # for sending replay data to buffer
        self.push_socket = ctx.socket(zmq.PUSH)
        self.push_socket.connect(f"tcp://127.0.0.1:{self.comm_cfg.worker_buffer_port}")

    def send_data_to_buffer(self, replay_data):
        """Send replay data to global buffer"""
        replay_data_id = pa.serialize(replay_data).to_buffer()
        self.push_socket.send(replay_data_id)

    def recv_params_from_learner(self):
        """Get new params and sync. return True if success, False otherwise"""
        received = False
        try:
            new_params_id = self.sub_socket.recv(zmq.DONTWAIT)
            received = True
        except zmq.Again:
            pass

        if received:
            new_param_info = pa.deserialize(new_params_id)
            update_step, new_params = new_param_info
            self.update_step = update_step
            self.worker.synchronize(new_params)

    def compute_priorities(self, experience: Dict[str, np.ndarray]):
        """Compute priority values (TD error) of collected experience"""
        return self.worker.compute_priorities(experience)

    def collect_data(self) -> dict:
        """Fill and return local buffer"""
        local_memory = [0]
        local_memory = dict(states=[], actions=[], rewards=[], next_states=[], dones=[])
        local_memory_keys = local_memory.keys()
        if self.use_n_step:
            nstep_queue = deque(maxlen=self.hyper_params.n_step)

        while len(local_memory["states"]) < self.hyper_params.local_buffer_max_size:
            state = self.worker.env.reset()
            done = False
            score = 0
            num_steps = 0
            while not done:
                if self.args.worker_render:
                    self.worker.env.render()
                num_steps += 1
                action = self.select_action(state)
                next_state, reward, done, _ = self.step(action)
                transition = (state, action, reward, next_state, int(done))
                if self.use_n_step:
                    nstep_queue.append(transition)
                    if self.hyper_params.n_step == len(nstep_queue):
                        nstep_exp = self.preprocess_nstep(nstep_queue)
                        for entry, keys in zip(nstep_exp, local_memory_keys):
                            local_memory[keys].append(entry)
                else:
                    for entry, keys in zip(transition, local_memory_keys):
                        local_memory[keys].append(entry)

                state = next_state
                score += reward

                self.recv_params_from_learner()

            if self.args.worker_verbose:
                print(
                    "[TRAIN] [Worker %d] Score: %d, Epsilon: %.5f "
                    % (self.worker.rank, score, self.worker.epsilon)
                )

        for key in local_memory_keys:
            local_memory[key] = np.array(local_memory[key])

        return local_memory

    def run(self):
        """Run main worker loop"""
        while self.update_step < self.args.max_update_step:
            experience = self.collect_data()
            priority_values = self.compute_priorities(experience)
            worker_data = [experience, priority_values]
            self.send_data_to_buffer(worker_data)
