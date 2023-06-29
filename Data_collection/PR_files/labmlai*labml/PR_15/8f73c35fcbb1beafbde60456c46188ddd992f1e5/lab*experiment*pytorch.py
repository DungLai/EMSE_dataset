import json
import pathlib
from typing import Optional, Dict, Set

import numpy as np
import torch.nn

from lab import experiment
from lab.logger.internal import CheckpointSaver


class Checkpoint(CheckpointSaver):
    __models: Dict[str, torch.nn.Module]

    def __init__(self, path: pathlib.PurePath):
        self.path = path
        self.__models = {}

    def add_models(self, models: Dict[str, torch.nn.Module]):
        """
        ## Set variable for saving and loading
        """
        self.__models.update(models)

    def save(self, global_step):
        """
        ## Save model as a set of numpy arrays
        """

        checkpoints_path = pathlib.Path(self.path)
        if not checkpoints_path.exists():
            checkpoints_path.mkdir()

        checkpoint_path = checkpoints_path / str(global_step)
        assert not checkpoint_path.exists()

        checkpoint_path.mkdir()

        files = {}
        for name, model in self.__models.items():
             state = model.state_dict()
             file_name = f"{name}.pth"
             files[name] = file_name
             torch.save(state, str(checkpoint_path / file_name))

        # Save header
        with open(str(checkpoint_path / "info.json"), "w") as f:
            f.write(json.dumps(files))

        # Delete old checkpoints
        # for c in checkpoints_path.iterdir():
        #     if c.name != checkpoint_path.name:
        #         util.rm_tree(c)

    def load(self, checkpoint_path):
        """
        ## Load model as a set of numpy arrays
        """

        with open(str(checkpoint_path / "info.json"), "r") as f:
            files = json.loads(f.readline())

        # Load each variable
        for name, model in self.__models.items():
            file_name = files[name]
            state = torch.load(str(checkpoint_path / file_name))

            model.load_state_dict(state)

        return True


class Experiment(experiment.Experiment):
    """
    ## Experiment

    Each experiment has different configurations or algorithms.
    An experiment can have multiple trials.
    """

    __checkpoint_saver: Checkpoint

    def __init__(self, *,
                 name: Optional[str] = None,
                 python_file: Optional[str] = None,
                 comment: Optional[str] = None,
                 writers: Set[str] = None,
                 ignore_callers: Set[str] = None,
                 tags: Optional[Set[str]] = None):
        """
        ### Create the experiment

        :param name: name of the experiment
        :param python_file: `__file__` that invokes this. This is stored in
         the experiments list.
        :param comment: a short description of the experiment

        The experiments log keeps track of `python_file`, `name`, `comment` as
         well as the git commit.

        Experiment maintains the locations of checkpoints, logs, etc.
        """

        super().__init__(name=name,
                         python_file=python_file,
                         comment=comment,
                         writers=writers,
                         ignore_callers=ignore_callers,
                         tags=tags)

    def _create_checkpoint_saver(self):
        self.__checkpoint_saver = Checkpoint(self.run.checkpoint_path)
        return self.__checkpoint_saver

    def add_models(self, models: Dict[str, torch.nn.Module]):
        """
        ## Set variable for saving and loading
        """
        self.__checkpoint_saver.add_models(models)

    def _load_checkpoint(self, checkpoint_path: pathlib.PurePath):
        self.__checkpoint_saver.load(checkpoint_path)
