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
from easydict import EasyDict
import tensorflow as tf

from nn.common import Tasks
from nn.networks.segmentation.lm_segnet import LmSegnet
from nn.datasets.camvid import Camvid
from nn.data_processor import Sequence
from nn.pre_processor import (
    PerImageStandardization,
)
from nn.data_augmentor import (
    Brightness,
    Color,
    Contrast,
    FlipLeftRight,
    Hue,
)

IS_DEBUG = False

NETWORK_CLASS = LmSegnet
DATASET_CLASS = Camvid

IMAGE_SIZE = [360, 480]
BATCH_SIZE = 8
DATA_FORMAT = "NHWC"
TASK = Tasks.SEMANTIC_SEGMENTATION
CLASSES = DATASET_CLASS.classes

MAX_STEPS = 150000
SAVE_CHECKPOINT_STEPS = 3000
KEEP_CHECKPOINT_MAX = 5
TEST_STEPS = 1000
SUMMARISE_STEPS = 1000


# pretrain
IS_PRETRAIN = False
PRETRAIN_VARS = []
PRETRAIN_DIR = ""
PRETRAIN_FILE = ""

# for debug
# BATCH_SIZE = 2
# SUMMARISE_STEPS = 1
# IS_DEBUG = True

PRE_PROCESSOR = Sequence([
    PerImageStandardization(),
])
POST_PROCESSOR = None

NETWORK = EasyDict()
NETWORK.OPTIMIZER_CLASS = tf.train.AdamOptimizer
NETWORK.OPTIMIZER_KWARGS = {"learning_rate": 0.001}
NETWORK.IMAGE_SIZE = IMAGE_SIZE
NETWORK.BATCH_SIZE = BATCH_SIZE
NETWORK.DATA_FORMAT = DATA_FORMAT

DATASET = EasyDict()
DATASET.BATCH_SIZE = BATCH_SIZE
DATASET.DATA_FORMAT = DATA_FORMAT
DATASET.PRE_PROCESSOR = PRE_PROCESSOR

DATASET.AUGMENTOR = Sequence([
    Brightness((0.75, 1.25)),
    Color((0.75, 1.25)),
    Contrast((0.75, 1.25)),
    FlipLeftRight(),
    Hue((-10, 10)),
])
DATASET.ENABLE_PREFETCH = True
