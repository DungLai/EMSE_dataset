# -*- coding: utf-8 -*-
"""SAC agent from demonstration for episodic tasks in OpenAI Gym.

- Author: Curt Park
- Contact: curt.park@medipixel.io
- Paper: https://arxiv.org/pdf/1801.01290.pdf
         https://arxiv.org/pdf/1812.05905.pdf
         https://arxiv.org/pdf/1511.05952.pdf
         https://arxiv.org/pdf/1707.08817.pdf
"""

import pickle
import time
from typing import Tuple

import numpy as np
import torch

from rl_algorithms.common.buffer.replay_buffer import ReplayBuffer
from rl_algorithms.common.buffer.wrapper import PrioritizedBufferWrapper
import rl_algorithms.common.helper_functions as common_utils
from rl_algorithms.common.helper_functions import numpy2floattensor
from rl_algorithms.fd.sac_learner import SACfDLearner
from rl_algorithms.registry import AGENTS
from rl_algorithms.sac.agent import SACAgent

device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")


@AGENTS.register_module
class SACfDAgent(SACAgent):
    """SAC agent interacting with environment.

    Attrtibutes:
        memory (PrioritizedReplayBuffer): replay memory
        beta (float): beta parameter for prioritized replay buffer
        use_n_step (bool): whether or not to use n-step returns

    """

    # pylint: disable=attribute-defined-outside-init
    def _initialize(self):
        """Initialize non-common things."""
        self.per_beta = self.hyper_params.per_beta
        self.use_n_step = self.hyper_params.n_step > 1

        if not self.args.test:
            # load demo replay memory
            with open(self.args.demo_path, "rb") as f:
                demos = pickle.load(f)

            if self.use_n_step:
                demos, demos_n_step = common_utils.get_n_step_info_from_demo(
                    demos, self.hyper_params.n_step, self.hyper_params.gamma
                )

                # replay memory for multi-steps
                self.memory_n = ReplayBuffer(
                    max_len=self.hyper_params.buffer_size,
                    batch_size=self.hyper_params.batch_size,
                    n_step=self.hyper_params.n_step,
                    gamma=self.hyper_params.gamma,
                    demo=demos_n_step,
                )

            # replay memory
            self.memory = ReplayBuffer(
                self.hyper_params.buffer_size, self.hyper_params.batch_size,
            )
            self.memory = PrioritizedBufferWrapper(
                self.memory, alpha=self.hyper_params.per_alpha
            )

        self.learner = SACfDLearner(
            self.args,
            self.hyper_params,
            self.log_cfg,
            self.head_cfg,
            self.backbone_cfg,
            self.optim_cfg,
            device,
        )

    def _add_transition_to_memory(self, transition: Tuple[np.ndarray, ...]):
        """Add 1 step and n step transitions to memory."""
        # add n-step transition
        if self.use_n_step:
            transition = self.memory_n.add(transition)

        # add a single step transition
        # if transition is not an empty tuple
        if transition:
            self.memory.add(transition)

    def sample_experience(self) -> Tuple[torch.Tensor, ...]:
        experience_1 = self.memory.sample(self.per_beta)
        if self.use_n_step:
            indices = experience_1[-2]
            experience_n = self.memory_n.sample(indices)
            return numpy2floattensor(experience_1), numpy2floattensor(experience_n)

        return numpy2floattensor(experience_1)

    def pretrain(self):
        """Pretraining steps."""
        pretrain_loss = list()
        pretrain_step = self.hyper_params.pretrain_step
        print("[INFO] Pre-Train %d steps." % pretrain_step)
        for i_step in range(1, pretrain_step + 1):
            t_begin = time.time()
            experience = self.sample_experience()
            info = self.learner.update_model(experience)
            loss = info[0:5]
            t_end = time.time()
            pretrain_loss.append(loss)  # for logging

            # logging
            if i_step == 1 or i_step % 100 == 0:
                avg_loss = np.vstack(pretrain_loss).mean(axis=0)
                pretrain_loss.clear()
                log_value = (
                    0,
                    avg_loss,
                    0,
                    self.hyper_params.policy_update_freq,
                    t_end - t_begin,
                )
                self.write_log(log_value)
        print("[INFO] Pre-Train Complete!\n")

    def train(self):
        """Train the agent."""
        # logger
        if self.args.log:
            self.set_wandb()
            # wandb.watch([self.actor, self.vf, self.qf_1, self.qf_2], log="parameters")

        # pre-training if needed
        self.pretrain()

        for self.i_episode in range(1, self.args.episode_num + 1):
            state = self.env.reset()
            done = False
            score = 0
            self.episode_step = 0
            loss_episode = list()

            t_begin = time.time()

            while not done:
                if self.args.render and self.i_episode >= self.args.render_after:
                    self.env.render()

                action = self.select_action(state)
                next_state, reward, done, _ = self.step(action)
                self.total_step += 1
                self.episode_step += 1

                state = next_state
                score += reward

                # training
                if len(self.memory) >= self.hyper_params.batch_size:
                    for _ in range(self.hyper_params.multiple_update):
                        experience = self.sample_experience()
                        info = self.learner.update_model(experience)
                        loss = info[0:5]
                        indices, new_priorities = info[5:7]
                        loss_episode.append(loss)  # for logging
                        self.memory.update_priorities(indices, new_priorities)

                # increase priority beta
                fraction = min(float(self.i_episode) / self.args.episode_num, 1.0)
                self.per_beta = self.per_beta + fraction * (1.0 - self.per_beta)

            t_end = time.time()
            avg_time_cost = (t_end - t_begin) / self.episode_step

            # logging
            if loss_episode:
                avg_loss = np.vstack(loss_episode).mean(axis=0)
                log_value = (
                    self.i_episode,
                    avg_loss,
                    score,
                    self.hyper_params.policy_update_freq,
                    avg_time_cost,
                )
                self.write_log(log_value)

            if self.i_episode % self.args.save_period == 0:
                self.learner.save_params(self.i_episode)
                self.interim_test()

        # termination
        self.env.close()
        self.learner.save_params(self.i_episode)
        self.interim_test()
