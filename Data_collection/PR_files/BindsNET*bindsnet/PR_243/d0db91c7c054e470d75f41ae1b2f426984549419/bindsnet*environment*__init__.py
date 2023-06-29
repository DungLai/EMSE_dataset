import gym
import torch
import numpy as np

from typing import Tuple, Dict, Any
from abc import ABC, abstractmethod

from ..datasets.spike_encoders import Encoder
from ..datasets.preprocess import subsample, gray_scale, binary_image, crop


class Environment(ABC):
    # language=rst
    """
    Abstract environment class.
    """

    @abstractmethod
    def step(self, a: int) -> Tuple[Any, ...]:
        # language=rst
        """
        Abstract method head for ``step()``.

        :param a: Integer action to take in environment.
        """
        pass

    @abstractmethod
    def reset(self) -> None:
        # language=rst
        """
        Abstract method header for ``reset()``.
        """
        pass

    @abstractmethod
    def render(self) -> None:
        # language=rst
        """
        Abstract method header for ``render()``.
        """
        pass

    @abstractmethod
    def close(self) -> None:
        # language=rst
        """
        Abstract method header for ``close()``.
        """
        pass

    @abstractmethod
    def preprocess(self) -> None:
        # language=rst
        """
        Abstract method header for ``preprocess()``.
        """
        pass


class GymEnvironment(Environment):
    # language=rst
    """
    A wrapper around the OpenAI ``gym`` environments.
    """

    def __init__(self, name: str, encoder: Encoder, **kwargs) -> None:
        # language=rst
        """
        Initializes the environment wrapper.

        :param name: The name of an OpenAI :code:`gym` environment.
        :param encoder: Function to encode observations into spike trains.

        Keyword arguments:

        :param max_prob: Maximum spiking probability.
        :param clip_rewards: Whether or not to use :code:`np.sign` of rewards.

        :param int history: Number of observations to keep track of.
        :param int delta: Step size to save observations in history.
        """
        self.name = name
        self.env = gym.make(name)
        self.action_space = self.env.action_space
        self.encoder = encoder

        # Keyword arguments.
        self.max_prob = kwargs.get("max_prob", 1)
        self.clip_rewards = kwargs.get("clip_rewards", True)

        self.history_length = kwargs.get('history_length', None)
        self.delta = kwargs.get('delta', 1)

        if self.history_length is not None and self.delta is not None:
            self.history = {i: torch.Tensor() for i in range(1, self.history_length * self.delta + 1, self.delta)}
        else:
            self.history = {}

        self.episode_step_count = 0
        self.history_index = 1

        self.obs = None
        self.reward = None

        assert 0 < self.max_prob <= 1, "Maximum spiking probability must be in (0, 1]."

    def step(self, a: int) -> Tuple[torch.Tensor, float, bool, Dict[Any, Any]]:
        # language=rst
        """
        Wrapper around the OpenAI Gym environment :code:`step()` function.

        :param a: Action to take in the environment.
        :return: Observation, reward, done flag, and information dictionary.
        """
        # Call gym's environment step function.
        self.obs, self.reward, self.done, info = self.env.step(a)

        if self.clip_rewards:
            self.reward = np.sign(self.reward)

        self.preprocess()

        # Store frame of history and encode the inputs.
        if len(self.history) > 0:
            self.update_history()
            self.update_index()

        raw_obs = self.obs

        # The new standard is BxTxCxHxW. The gym environment doesn't
        # follow exactly the same protocol.
        self.obs = self.encoder(self.obs).unsqueeze(1)
        if self.obs.dim() == 4:
            self.obs = self.obs.unsqueeze(2)

        self.episode_step_count += 1

        # Return converted observations and other information.
        return {"obs": self.obs,
                "reward": self.reward,
                "done": self.done,
                "info": info,
                "raw_obs": raw_obs}

    def reset(self) -> torch.Tensor:
        # language=rst
        """
        Wrapper around the OpenAI Gym environment :code:`reset()` function.

        :return: Observation from the environment.
        """
        # Call gym's environment reset function.
        self.obs = self.env.reset()
        self.preprocess()

        self.history = {i: torch.Tensor() for i in self.history}

        self.episode_step_count = 0

        return self.obs

    def render(self) -> None:
        # language=rst
        """
        Wrapper around the OpenAI Gym environment :code:`render()` function.
        """
        self.env.render()

    def close(self) -> None:
        # language=rst
        """
        Wrapper around the OpenAI Gym environment :code:`close()` function.
        """
        self.env.close()

    def preprocess(self) -> None:
        # language=rst
        """
        Pre-processing step for an observation from a Gym environment.
        """
        if self.name == "SpaceInvaders-v0":
            self.obs = subsample(gray_scale(self.obs), 84, 110)
            self.obs = self.obs[26:104, :]
            self.obs = binary_image(self.obs)
        elif self.name == "BreakoutDeterministic-v4":
            self.obs = subsample(gray_scale(crop(self.obs, 34, 194, 0, 160)), 80, 80)
            self.obs = binary_image(self.obs)
        else:  # Default pre-processing step
            self.obs = subsample(gray_scale(self.obs), 84, 110)
            self.obs = binary_image(self.obs)

        self.obs = torch.from_numpy(self.obs).float()

    def update_history(self) -> None:
        # language=rst
        """
        Updates the observations inside history by performing subtraction from  most recent observation and the sum of
        previous observations. If there are not enough observations to take a difference from, simply store the
        observation without any differencing.
        """
        # Recording initial observations
        if self.episode_step_count < len(self.history) * self.delta:
            # Store observation based on delta value
            if self.episode_step_count % self.delta == 0:
                self.history[self.history_index] = self.obs
        else:
            # Take difference between stored frames and current frame
            temp = torch.clamp(self.obs - sum(self.history.values()), 0, 1)

            # Store observation based on delta value.
            if self.episode_step_count % self.delta == 0:
                self.history[self.history_index] = self.obs

            assert (len(self.history) == self.history_length), 'History size is out of bounds'
            self.obs = temp

    def update_index(self) -> None:
        # language=rst
        """
        Updates the index to keep track of history. For example: history = 4, delta = 3 will produce self.history = {1,
        4, 7, 10} and self.history_index will be updated according to self.delta and will wrap around the history
        dictionary.
        """
        if self.episode_step_count % self.delta == 0:
            if self.history_index != max(self.history.keys()):
                self.history_index += self.delta
            else:
                # Wrap around the history.
                self.history_index = (self.history_index % max(self.history.keys())) + 1