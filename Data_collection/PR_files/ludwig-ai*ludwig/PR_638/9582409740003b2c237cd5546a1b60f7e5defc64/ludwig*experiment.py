#! /usr/bin/env python
# coding=utf-8
# Copyright (c) 2019 Uber Technologies, Inc.
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
# ==============================================================================
from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import argparse
import logging
import os
import sys
import tempfile

import numpy as np
import pandas as pd
import yaml

from ludwig.constants import TRAINING
from ludwig.contrib import contrib_command
from ludwig.data.postprocessing import postprocess
from ludwig.globals import LUDWIG_VERSION, set_on_master, is_on_master
from ludwig.predict import predict
from ludwig.predict import print_test_results
from ludwig.predict import save_prediction_outputs
from ludwig.predict import save_test_statistics
from ludwig.train import full_train, logger
from ludwig.utils.data_utils import save_json, generate_kfold_splits
from ludwig.utils.defaults import default_random_seed, merge_with_defaults
from ludwig.utils.print_utils import logging_level_registry
from ludwig.utils.print_utils import print_ludwig

logger = logging.getLogger(__name__)


def experiment(
        model_definition,
        model_definition_file=None,
        data_df=None,
        data_train_df=None,
        data_validation_df=None,
        data_test_df=None,
        data_csv=None,
        data_train_csv=None,
        data_validation_csv=None,
        data_test_csv=None,
        data_hdf5=None,
        data_train_hdf5=None,
        data_validation_hdf5=None,
        data_test_hdf5=None,
        train_set_metadata_json=None,
        experiment_name='experiment',
        model_name='run',
        model_load_path=None,
        model_resume_path=None,
        skip_save_training_description=False,
        skip_save_training_statistics=False,
        skip_save_model=False,
        skip_save_progress=False,
        skip_save_log=False,
        skip_save_processed_input=False,
        skip_save_unprocessed_output=False,  # skipcq: PYL-W0613
        skip_save_test_predictions=False,  # skipcq: PYL-W0613
        skip_save_test_statistics=False,  # skipcq: PYL-W0613
        output_directory='results',
        should_close_session=False,
        gpus=None,
        gpu_fraction=1.0,
        use_horovod=False,
        random_seed=default_random_seed,
        debug=False,
        **kwargs
):
    (
        model,
        preprocessed_data,
        experiment_dir_name,
        train_stats,
        model_definition
    ) = full_train(
        model_definition,
        model_definition_file=model_definition_file,
        data_df=data_df,
        data_train_df=data_train_df,
        data_validation_df=data_validation_df,
        data_test_df=data_test_df,
        data_csv=data_csv,
        data_train_csv=data_train_csv,
        data_validation_csv=data_validation_csv,
        data_test_csv=data_test_csv,
        data_hdf5=data_hdf5,
        data_train_hdf5=data_train_hdf5,
        data_validation_hdf5=data_validation_hdf5,
        data_test_hdf5=data_test_hdf5,
        train_set_metadata_json=train_set_metadata_json,
        experiment_name=experiment_name,
        model_name=model_name,
        model_load_path=model_load_path,
        model_resume_path=model_resume_path,
        skip_save_training_description=skip_save_training_description,
        skip_save_training_statistics=skip_save_training_statistics,
        skip_save_model=skip_save_model,
        skip_save_progress=skip_save_progress,
        skip_save_log=skip_save_log,
        skip_save_processed_input=skip_save_processed_input,
        output_directory=output_directory,
        should_close_session=should_close_session,
        gpus=gpus,
        gpu_fraction=gpu_fraction,
        use_horovod=use_horovod,
        random_seed=random_seed,
        debug=debug,
        **kwargs
    )

    (_,  # training_set
     _,  # validation_set
     test_set,
     train_set_metadata) = preprocessed_data

    if test_set is not None:
        if model_definition[TRAINING]['eval_batch_size'] > 0:
            batch_size = model_definition[TRAINING]['eval_batch_size']
        else:
            batch_size = model_definition[TRAINING]['batch_size']

        # predict
        test_results = predict(
            test_set,
            train_set_metadata,
            model,
            model_definition,
            batch_size,
            evaluate_performance=True,
            gpus=gpus,
            gpu_fraction=gpu_fraction,
            debug=debug
        )
    else:
        test_results = None

    return (
        model,
        preprocessed_data,
        experiment_dir_name,
        train_stats,
        model_definition,
        test_results
    )


def full_experiment(
        model_definition,
        model_definition_file=None,
        data_df=None,
        data_train_df=None,
        data_validation_df=None,
        data_test_df=None,
        data_csv=None,
        data_train_csv=None,
        data_validation_csv=None,
        data_test_csv=None,
        data_hdf5=None,
        data_train_hdf5=None,
        data_validation_hdf5=None,
        data_test_hdf5=None,
        train_set_metadata_json=None,
        experiment_name='experiment',
        model_name='run',
        model_load_path=None,
        model_resume_path=None,
        skip_save_training_description=False,
        skip_save_training_statistics=False,
        skip_save_model=False,
        skip_save_progress=False,
        skip_save_log=False,
        skip_save_processed_input=False,
        skip_save_unprocessed_output=False,
        skip_save_test_predictions=False,
        skip_save_test_statistics=False,
        output_directory='results',
        gpus=None,
        gpu_fraction=1.0,
        use_horovod=False,
        random_seed=default_random_seed,
        debug=False,
        **kwargs
):
    """Trains a model on a dataset's training and validation splits and
    uses it to predict on the test split.
    It saves the trained model and the statistics of training and testing.
    :param model_definition: Model definition which defines the different
           parameters of the model, features, preprocessing and training.
    :type model_definition: Dictionary
    :param model_definition_file: The file that specifies the model definition.
           It is a yaml file.
    :type model_definition_file: filepath (str)
    :param data_csv: A CSV file containing the input data which is used to
           train, validate and test a model. The CSV either contains a
           split column or will be split.
    :type data_csv: filepath (str)
    :param data_train_csv: A CSV file containing the input data which is used
           to train a model.
    :type data_train_csv: filepath (str)
    :param data_validation_csv: A CSV file containing the input data which is used
           to validate a model..
    :type data_validation_csv: filepath (str)
    :param data_test_csv: A CSV file containing the input data which is used
           to test a model.
    :type data_test_csv: filepath (str)
    :param data_hdf5: If the dataset is in the hdf5 format, this is used instead
           of the csv file.
    :type data_hdf5: filepath (str)
    :param data_train_hdf5: If the training set is in the hdf5 format, this is
           used instead of the csv file.
    :type data_train_hdf5: filepath (str)
    :param data_validation_hdf5: If the validation set is in the hdf5 format,
           this is used instead of the csv file.
    :type data_validation_hdf5: filepath (str)
    :param data_test_hdf5: If the test set is in the hdf5 format, this is
           used instead of the csv file.
    :type data_test_hdf5: filepath (str)
    :param train_set_metadata_json: If the dataset is in hdf5 format, this is
           the associated json file containing metadata.
    :type train_set_metadata_json: filepath (str)
    :param experiment_name: The name for the experiment.
    :type experiment_name: Str
    :param model_name: Name of the model that is being used.
    :type model_name: Str
    :param model_load_path: If this is specified the loaded model will be used
           as initialization (useful for transfer learning).
    :type model_load_path: filepath (str)
    :param model_resume_path: Resumes training of the model from the path
           specified. The difference with model_load_path is that also training
           statistics like the current epoch and the loss and performance so
           far are also resumed effectively continuing a previously interrupted
           training process.
    :type model_resume_path: filepath (str)
    :param skip_save_training_description: Disables saving
           the description JSON file.
    :type skip_save_training_description: Boolean
    :param skip_save_training_statistics: Disables saving
           training statistics JSON file.
    :type skip_save_training_statistics: Boolean
    :param skip_save_model: Disables
               saving model weights and hyperparameters each time the model
           improves. By default Ludwig saves model weights after each epoch
           the validation measure improves, but if the model is really big
           that can be time consuming if you do not want to keep
           the weights and just find out what performance can a model get
           with a set of hyperparameters, use this parameter to skip it,
           but the model will not be loadable later on.
    :type skip_save_model: Boolean
    :param skip_save_progress: Disables saving
           progress each epoch. By default Ludwig saves weights and stats
           after each epoch for enabling resuming of training, but if
           the model is really big that can be time consuming and will uses
           twice as much space, use this parameter to skip it, but training
           cannot be resumed later on.
    :type skip_save_progress: Boolean
    :param skip_save_log: Disables saving TensorBoard
           logs. By default Ludwig saves logs for the TensorBoard, but if it
           is not needed turning it off can slightly increase the
           overall speed..
    :type skip_save_log: Boolean
    :param skip_save_processed_input: If a CSV dataset is provided it is
           preprocessed and then saved as an hdf5 and json to avoid running
           the preprocessing again. If this parameter is False,
           the hdf5 and json file are not saved.
    :type skip_save_processed_input: Boolean
    :param skip_save_unprocessed_output: By default predictions and
           their probabilities are saved in both raw unprocessed numpy files
           containing tensors and as postprocessed CSV files
           (one for each output feature). If this parameter is True,
           only the CSV ones are saved and the numpy ones are skipped.
    :type skip_save_unprocessed_output: Boolean
    :param skip_save_test_predictions: skips saving test predictions CSV files
    :type skip_save_test_predictions: Boolean
    :param skip_save_test_statistics: skips saving test statistics JSON file
    :type skip_save_test_statistics: Boolean
    :param output_directory: The directory that will contain the training
           statistics, the saved model and the training progress files.
    :type output_directory: filepath (str)
    :param gpus: List of GPUs that are available for training.
    :type gpus: List
    :param gpu_fraction: Fraction of the memory of each GPU to use at
           the beginning of the training. The memory may grow elastically.
    :type gpu_fraction: Integer
    :param use_horovod: Flag for using horovod
    :type use_horovod: Boolean
    :param random_seed: Random seed used for weights initialization,
           splits and any other random function.
    :type random_seed: Integer
    :param debug: If true turns on tfdbg with inf_or_nan checks.
    :type debug: Boolean
    """

    (
        model,
        preprocessed_data,
        experiment_dir_name,
        _,  # train_stats
        model_definition,
        test_results
    ) = experiment(
        model_definition,
        model_definition_file=model_definition_file,
        data_df=data_df,
        data_train_df=data_train_df,
        data_validation_df=data_validation_df,
        data_test_df=data_test_df,
        data_csv=data_csv,
        data_train_csv=data_train_csv,
        data_validation_csv=data_validation_csv,
        data_test_csv=data_test_csv,
        data_hdf5=data_hdf5,
        data_train_hdf5=data_train_hdf5,
        data_validation_hdf5=data_validation_hdf5,
        data_test_hdf5=data_test_hdf5,
        train_set_metadata_json=train_set_metadata_json,
        experiment_name=experiment_name,
        model_name=model_name,
        model_load_path=model_load_path,
        model_resume_path=model_resume_path,
        skip_save_training_description=skip_save_training_description,
        skip_save_training_statistics=skip_save_training_statistics,
        skip_save_model=skip_save_model,
        skip_save_progress=skip_save_progress,
        skip_save_log=skip_save_log,
        skip_save_processed_input=skip_save_processed_input,
        output_directory=output_directory,
        should_close_session=False,
        gpus=gpus,
        gpu_fraction=gpu_fraction,
        use_horovod=use_horovod,
        random_seed=random_seed,
        debug=debug,
        **kwargs
    )

    (training_set,
     validation_set,
     test_set,
     train_set_metadata) = preprocessed_data

    if test_set is not None:
        # check if we need to create the output dir
        if is_on_master():
            if not (
                    skip_save_unprocessed_output and
                    skip_save_test_predictions and
                    skip_save_test_statistics
            ):
                if not os.path.exists(experiment_dir_name):
                    os.makedirs(experiment_dir_name)

        # postprocess
        postprocessed_output = postprocess(
            test_results,
            model_definition['output_features'],
            train_set_metadata,
            experiment_dir_name,
            skip_save_unprocessed_output or not is_on_master()
        )

        if is_on_master():
            print_test_results(test_results)
            if not skip_save_test_predictions:
                save_prediction_outputs(
                    postprocessed_output,
                    experiment_dir_name
                )
            if not skip_save_test_statistics:
                save_test_statistics(test_results, experiment_dir_name)

    model.close_session()

    if is_on_master():
        logger.info('\nFinished: {0}_{1}'.format(
            experiment_name, model_name))
        logger.info('Saved to: {}'.format(experiment_dir_name))

    contrib_command("experiment_save", experiment_dir_name)
    return experiment_dir_name


def kfold_cross_validate(
        k_fold,
        model_definition=None,
        model_definition_file=None,
        data_csv=None,
        output_directory='results',
        random_seed=default_random_seed,
        **kwargs
):
    # check for k_fold
    if k_fold is None:
        raise ValueError(
            'k_fold parameter must be specified'
        )

    # check for model_definition and model_definition_file
    if model_definition is None and model_definition_file is None:
        raise ValueError(
            'Either model_definition of model_definition_file have to be'
            'not None to initialize a LudwigModel'
        )
    if model_definition is not None and model_definition_file is not None:
        raise ValueError(
            'Only one between model_definition and '
            'model_definition_file can be provided'
        )

    logger.info('starting {:d}-fold cross validation'.format(k_fold))

    # extract out model definition for use
    if model_definition_file is not None:
        with open(model_definition_file, 'r') as def_file:
            model_definition = \
                merge_with_defaults(yaml.safe_load(def_file))

    # create output_directory if not available
    if not os.path.isdir(output_directory):
        os.mkdir(output_directory)

    # read in data to split for the folds
    data_df = pd.read_csv(data_csv)

    # place each fold in a separate directory
    data_dir = os.path.dirname(data_csv)

    kfold_cv_stats = {}
    kfold_split_indices = {}

    for train_indices, test_indices, fold_num in \
            generate_kfold_splits(data_df, k_fold, random_seed):
        with tempfile.TemporaryDirectory(dir=data_dir) as temp_dir_name:
            curr_train_df = data_df.iloc[train_indices]
            curr_test_df = data_df.iloc[test_indices]

            kfold_split_indices['fold_' + str(fold_num)] = {
                'training_indices': train_indices,
                'test_indices': test_indices
            }

            # train and validate model on this fold
            logger.info("training on fold {:d}".format(fold_num))
            (
                _,  # model
                _,  # preprocessed_data
                _,  # experiment_dir_name
                train_stats,
                model_definition,
                test_results
            ) = experiment(
                model_definition,
                data_train_df=curr_train_df,
                data_test_df=curr_test_df,
                experiment_name='cross_validation',
                model_name='fold_' + str(fold_num),
                output_directory=os.path.join(temp_dir_name, 'results')
            )

            # augment the training statistics with scoring metric from
            # the hold out fold
            train_stats['fold_metric'] = {}
            for metric_category in test_results:
                train_stats['fold_metric'][metric_category] = {}
                for metric in test_results[metric_category]:
                    train_stats['fold_metric'][metric_category][metric] = \
                        test_results[metric_category][metric]

            # collect training statistics for this fold
            kfold_cv_stats['fold_' + str(fold_num)] = train_stats

    # consolidate raw fold metrics across all folds
    raw_kfold_stats = {}
    for fold_name in kfold_cv_stats:
        for category in kfold_cv_stats[fold_name]['fold_metric']:
            if category not in raw_kfold_stats:
                raw_kfold_stats[category] = {}
            category_stats = \
                kfold_cv_stats[fold_name]['fold_metric'][category]
            for metric in category_stats:
                if metric not in {
                    'predictions',
                    'probabilities',
                    'confusion_matrix',
                    'overall_stats',
                    'per_class_stats',
                    'roc_curve',
                    'precision_recall_curve'
                }:
                    if metric not in raw_kfold_stats[category]:
                        raw_kfold_stats[category][metric] = []
                    raw_kfold_stats[category][metric] \
                        .append(category_stats[metric])

    # calculate overall kfold statistics
    overall_kfold_stats = {}
    for category in raw_kfold_stats:
        overall_kfold_stats[category] = {}
        for metric in raw_kfold_stats[category]:
            mean = np.mean(raw_kfold_stats[category][metric])
            std = np.std(raw_kfold_stats[category][metric])
            overall_kfold_stats[category][metric + '_mean'] = mean
            overall_kfold_stats[category][metric + '_std'] = std

    kfold_cv_stats['overall'] = overall_kfold_stats

    logger.info('completed {:d}-fold cross validation'.format(k_fold))

    return kfold_cv_stats, kfold_split_indices


def full_kfold_cross_validate(
        k_fold,
        model_definition=None,
        model_definition_file=None,
        data_csv=None,
        output_directory='results',
        random_seed=default_random_seed,
        skip_save_k_fold_split_indices=False,
        **kwargs
):
    """Wrapper function to performs k-fold cross validation.

    # Inputs
    :param k_fold: (int) number of folds to create for the cross-validation
    :param model_definition: (dict, default: None) a dictionary containing
            information needed to build a model. Refer to the [User Guide]
           (http://ludwig.ai/user_guide/#model-definition) for details.
    :param model_definition_file: (string, optional, default: `None`) path to
           a YAML file containing the model definition. If available it will be
           used instead of the model_definition dict.
    :param data_csv: (string, default: None)
    :param output_directory: (string, default: 'results')
    :param random_seed: (int) Random seed used k-fold splits.
    :param skip_save_k_fold_split_indices: (boolean, default: False) Disables
            saving k-fold split indices

    :return: None
    """

    (kfold_cv_stats,
     kfold_split_indices) = kfold_cross_validate(
        k_fold,
        model_definition=model_definition,
        model_definition_file=model_definition_file,
        data_csv=data_csv,
        output_directory=output_directory,
        random_seed=random_seed
    )

    # save k-fold cv statistics
    save_json(os.path.join(output_directory, 'kfold_training_statistics.json'),
              kfold_cv_stats)

    # save k-fold split indices
    if not skip_save_k_fold_split_indices:
        save_json(os.path.join(output_directory, 'kfold_split_indices.json'),
                  kfold_split_indices)


def cli(sys_argv):
    parser = argparse.ArgumentParser(
        description='This script trains and tests a model',
        prog='ludwig experiment',
        usage='%(prog)s [options]'
    )

    # ----------------------------
    # Experiment naming parameters
    # ----------------------------
    parser.add_argument(
        '--output_directory',
        type=str,
        default='results',
        help='directory that contains the results'
    )
    parser.add_argument(
        '--experiment_name',
        type=str,
        default='experiment',
        help='experiment name'
    )
    parser.add_argument(
        '--model_name',
        type=str,
        default='run',
        help='name for the model'
    )

    # ---------------
    # Data parameters
    # ---------------
    parser.add_argument(
        '--data_csv',
        help='input data CSV file. If it has a split column, it will be used '
             'for splitting (0: train, 1: validation, 2: test), otherwise the '
             'dataset will be randomly split'
    )
    parser.add_argument('--data_train_csv', help='input train data CSV file')
    parser.add_argument(
        '--data_validation_csv',
        help='input validation data CSV file'
    )
    parser.add_argument('--data_test_csv', help='input test data CSV file')

    parser.add_argument(
        '--data_hdf5',
        help='input data HDF5 file. It is an intermediate preprocess version of'
             ' the input CSV created the first time a CSV file is used in the '
             'same directory with the same name and a hdf5 extension'
    )
    parser.add_argument(
        '--data_train_hdf5',
        help='input train data HDF5 file. It is an intermediate preprocess '
             'version of the input CSV created the first time a CSV file is '
             'used in the same directory with the same name and a hdf5 '
             'extension'
    )
    parser.add_argument(
        '--data_validation_hdf5',
        help='input validation data HDF5 file. It is an intermediate preprocess'
             ' version of the input CSV created the first time a CSV file is '
             'used in the same directory with the same name and a hdf5 '
             'extension'
    )
    parser.add_argument(
        '--data_test_hdf5',
        help='input test data HDF5 file. It is an intermediate preprocess '
             'version of the input CSV created the first time a CSV file is '
             'used in the same directory with the same name and a hdf5 '
             'extension'
    )

    parser.add_argument(
        '--metadata_json',
        help='input metadata JSON file. It is an intermediate preprocess file'
             ' containing the mappings of the input CSV created the first time '
             'a CSV file is used in the same directory with the same name and a'
             ' json extension'
    )

    parser.add_argument(
        '-sspi',
        '--skip_save_processed_input',
        help='skips saving intermediate HDF5 and JSON files',
        action='store_true',
        default=False
    )
    parser.add_argument(
        '-ssuo',
        '--skip_save_unprocessed_output',
        help='skips saving intermediate NPY output files',
        action='store_true',
        default=False
    )

    # -----------------
    # K-fold parameters
    # -----------------
    parser.add_argument(
        '-kf',
        '--k_fold',
        type=int,
        default=None,
        help='number of folds for a k-fold cross validation run '
    )
    parser.add_argument(
        '-skfsi',
        '--skip_save_k_fold_split_indices',
        action='store_true',
        default=False,
        help='disables saving indices generated to split training data set '
             'for the k-fold cross validation run, but if it is not needed '
             'turning it off can slightly increase the overall speed'
    )

    # ----------------
    # Model parameters
    # ----------------
    model_definition = parser.add_mutually_exclusive_group(required=True)
    model_definition.add_argument(
        '-md',
        '--model_definition',
        type=yaml.safe_load,
        help='model definition'
    )
    model_definition.add_argument(
        '-mdf',
        '--model_definition_file',
        help='YAML file describing the model. Ignores --model_hyperparameters'
    )

    parser.add_argument(
        '-mlp',
        '--model_load_path',
        help='path of a pretrained model to load as initialization'
    )
    parser.add_argument(
        '-mrp',
        '--model_resume_path',
        help='path of a the model directory to resume training of'
    )
    parser.add_argument(
        '-sstd',
        '--skip_save_training_description',
        action='store_true',
        default=False,
        help='disables saving the description JSON file'
    )
    parser.add_argument(
        '-ssts',
        '--skip_save_training_statistics',
        action='store_true',
        default=False,
        help='disables saving training statistics JSON file'
    )
    parser.add_argument(
        '-sstp',
        '--skip_save_test_predictions',
        help='skips saving test predictions CSV files',
        action='store_true', default=False
    )
    parser.add_argument(
        '-sstes',
        '--skip_save_test_statistics',
        help='skips saving test statistics JSON file',
        action='store_true', default=False
    )
    parser.add_argument(
        '-ssm',
        '--skip_save_model',
        action='store_true',
        default=False,
        help='disables saving model weights and hyperparameters each time '
             'the model improves. '
             'By default Ludwig saves model weights after each epoch '
             'the validation measure imprvoes, but if the model is really big '
             'that can be time consuming if you do not want to keep '
             'the weights and just find out what performance can a model get '
             'with a set of hyperparameters, use this parameter to skip it,'
             'but the model will not be loadable later on'
    )
    parser.add_argument(
        '-ssp',
        '--skip_save_progress',
        action='store_true',
        default=False,
        help='disables saving progress each epoch. By default Ludwig saves '
             'weights and stats  after each epoch for enabling resuming '
             'of training, but if the model is really big that can be '
             'time consuming and will uses twice as much space, use '
             'this parameter to skip it, but training cannot be resumed '
             'later on'
    )
    parser.add_argument(
        '-ssl',
        '--skip_save_log',
        action='store_true',
        default=False,
        help='disables saving TensorBoard logs. By default Ludwig saves '
             'logs for the TensorBoard, but if it is not needed turning it off '
             'can slightly increase the overall speed'
    )

    # ------------------
    # Runtime parameters
    # ------------------
    parser.add_argument(
        '-rs',
        '--random_seed',
        type=int,
        default=42,
        help='a random seed that is going to be used anywhere there is a call '
             'to a random number generator: data splitting, parameter '
             'initialization and training set shuffling'
    )
    parser.add_argument(
        '-g',
        '--gpus',
        nargs='+',
        type=int,
        default=None,
        help='list of GPUs to use'
    )
    parser.add_argument(
        '-gf',
        '--gpu_fraction',
        type=float,
        default=1.0,
        help='fraction of gpu memory to initialize the process with'
    )
    parser.add_argument(
        '-uh',
        '--use_horovod',
        action='store_true',
        default=False,
        help='uses horovod for distributed training'
    )
    parser.add_argument(
        '-dbg',
        '--debug',
        action='store_true',
        default=False,
        help='enables debugging mode'
    )
    parser.add_argument(
        '-l',
        '--logging_level',
        default='info',
        help='the level of logging to use',
        choices=['critical', 'error', 'warning', 'info', 'debug', 'notset']
    )

    args = parser.parse_args(sys_argv)

    logging.getLogger('ludwig').setLevel(
        logging_level_registry[args.logging_level]
    )

    set_on_master(args.use_horovod)

    if is_on_master():
        print_ludwig('Experiment', LUDWIG_VERSION)

    if args.k_fold is None:
        full_experiment(**vars(args))
    else:
        full_kfold_cross_validate(**vars(args))


if __name__ == '__main__':
    contrib_command("experiment", *sys.argv)
    cli(sys.argv[1:])
