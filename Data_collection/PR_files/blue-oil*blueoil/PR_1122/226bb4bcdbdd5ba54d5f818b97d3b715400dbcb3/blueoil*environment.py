# -*- coding: utf-8 -*-
# Copyright 2018 The Blueoil Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================
import os

EXPERIMENT_ID = None
EXPERIMENT_DIR = None
TENSORBOARD_DIR = None
CHECKPOINTS_DIR = None

default_data_dir = "dataset"
DATA_DIR = os.getenv("DATA_DIR", os.path.join(os.getcwd(), default_data_dir))

default_output_dir = "saved"
OUTPUT_DIR = os.getenv("OUTPUT_DIR", os.path.join(os.getcwd(), default_output_dir))

_EXPERIMENT_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}")
_TENSORBOARD_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}", "tensorboard")
_CHECKPOINTS_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}", "checkpoints")


def set_data_dir(path):
    global DATA_DIR
    DATA_DIR = path if is_gcs_path(path) else os.path.abspath(path)
    os.environ["DATA_DIR"] = DATA_DIR


def set_output_dir(path):
    global OUTPUT_DIR
    OUTPUT_DIR = path if is_gcs_path(path) else os.path.abspath(path)
    os.environ["OUTPUT_DIR"] = OUTPUT_DIR

    global _EXPERIMENT_DIR, _TENSORBOARD_DIR, _CHECKPOINTS_DIR
    _EXPERIMENT_DIR = os.path.join(
        OUTPUT_DIR, "{experiment_id}",
    )
    _TENSORBOARD_DIR = os.path.join(
        OUTPUT_DIR, "{experiment_id}", "tensorboard",
    )
    _CHECKPOINTS_DIR = os.path.join(
        OUTPUT_DIR, "{experiment_id}", "checkpoints",
    )

    global EXPERIMENT_ID
    if EXPERIMENT_ID:
        init(EXPERIMENT_ID)


def init(experiment_id):
    """Initialize experiment environment.

    experiment id embed to directories.
    """
    global EXPERIMENT_ID, EXPERIMENT_DIR, TENSORBOARD_DIR, CHECKPOINTS_DIR

    # remove OUTPUT_DIR if it be included in experiment_id.
    if OUTPUT_DIR + os.path.sep in experiment_id:
        experiment_id = experiment_id.replace(OUTPUT_DIR + os.path.sep, "")
    EXPERIMENT_ID = experiment_id

    EXPERIMENT_DIR = _EXPERIMENT_DIR.format(experiment_id=experiment_id)

    # directory to save this experiment outputs for tensorboard.
    TENSORBOARD_DIR = _TENSORBOARD_DIR.format(experiment_id=experiment_id)

    # checkpoints_dir in the same way of tensorboard_dir.
    CHECKPOINTS_DIR = _CHECKPOINTS_DIR.format(experiment_id=experiment_id)


def setup_test_environment():
    """Override `OUTPUT_DIR` and `DATA_DIR` for test."""
    global DATA_DIR, _EXPERIMENT_DIR, _TENSORBOARD_DIR, _CHECKPOINTS_DIR

    DATA_DIR = "unit/fixtures/datasets"

    OUTPUT_DIR = "tmp/tests/saved"

    _EXPERIMENT_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}")
    _TENSORBOARD_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}", "tensorboard")
    _CHECKPOINTS_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}", "checkpoints")


def teardown_test_environment():
    """Reset test environment."""
    global DATA_DIR, _EXPERIMENT_DIR, _TENSORBOARD_DIR, _CHECKPOINTS_DIR

    default_data_dir = "dataset"
    DATA_DIR = os.getenv("DATA_DIR", default_data_dir)

    default_output_dir = "saved"
    OUTPUT_DIR = os.getenv("OUTPUT_DIR", default_output_dir)

    _EXPERIMENT_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}")
    _TENSORBOARD_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}", "tensorboard")
    _CHECKPOINTS_DIR = os.path.join(OUTPUT_DIR, "{experiment_id}", "checkpoints")


def is_gcs_path(path):
    """Check argument string is GCS path or not
    Args:
        path: Path like string
    Returns:
        True when string is GCS path
    """
    return path[0:5] == "gs://"
