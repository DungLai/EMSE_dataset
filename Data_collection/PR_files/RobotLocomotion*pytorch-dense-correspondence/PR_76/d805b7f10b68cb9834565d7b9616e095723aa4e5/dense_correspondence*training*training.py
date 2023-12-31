# system
import numpy as np
import os
import fnmatch
import gc
import logging
import time
import shutil
import subprocess

# torch
import torch
from torchvision import transforms
from torch.autograd import Variable
import torch.nn as nn
import torch.optim as optim

import visdom
from torchnet.logger import VisdomPlotLogger, VisdomLogger



# dense correspondence
import dense_correspondence_manipulation.utils.utils as utils
utils.add_dense_correspondence_to_python_path()
import pytorch_segmentation_detection.models.fcn as fcns
import pytorch_segmentation_detection.models.resnet_dilated as resnet_dilated
from pytorch_segmentation_detection.transforms import (ComposeJoint,
                                                       RandomHorizontalFlipJoint,
                                                       RandomScaleJoint,
                                                       CropOrPad,
                                                       ResizeAspectRatioPreserve,
                                                       RandomCropJoint,
                                                       Split2D)

from dense_correspondence.dataset.spartan_dataset_masked import SpartanDataset
from dense_correspondence.network.dense_correspondence_network import DenseCorrespondenceNetwork

from dense_correspondence.loss_functions.pixelwise_contrastive_loss import PixelwiseContrastiveLoss
from dense_correspondence.evaluation.evaluation import DenseCorrespondenceEvaluation


class DenseCorrespondenceTraining(object):

    def __init__(self, config=None, dataset=None, dataset_test=None):
        if config is None:
            config = DenseCorrespondenceTraining.load_default_config()

        self._config = config
        self._dataset = dataset
        self._dataset_test = dataset_test

        self._dcn = None
        self._optimizer = None

    def setup(self):
        """
        Initializes the object
        :return:
        :rtype:
        """
        self.load_dataset()
        self.setup_logging_dir()
        self.setup_visdom()


    @property
    def dataset(self):
        return self._dataset

    @dataset.setter
    def dataset(self, value):
        self._dataset = value

    def load_dataset(self):
        """
        Loads a dataset, construct a trainloader.
        Additionally creates a dataset and DataLoader for the test data
        :return:
        :rtype:
        """

        batch_size = self._config['training']['batch_size']
        num_workers = self._config['training']['num_workers']

        if self._dataset is None:
            self._dataset = SpartanDataset.make_default_10_scenes_drill()

        

        self._dataset.load_all_pose_data()
        self._dataset.set_parameters_from_training_config(self._config)

        self._data_loader = torch.utils.data.DataLoader(self._dataset, batch_size=batch_size,
                                          shuffle=True, num_workers=num_workers, drop_last=True)

        # create a test dataset
        if self._dataset_test is None:
            self._dataset_test = SpartanDataset(mode="test", config=self._dataset.config)

        
        self._dataset_test.load_all_pose_data()
        self._dataset_test.set_parameters_from_training_config(self._config)

        self._data_loader_test = torch.utils.data.DataLoader(self._dataset_test, batch_size=batch_size,
                                          shuffle=True, num_workers=num_workers, drop_last=True)

    def load_dataset_from_config(self, config):
        """
        Loads train and test datasets from the given config
        :param config: Dict gotten from a YAML file
        :type config:
        :return: None
        :rtype:
        """
        self._dataset = SpartanDataset(mode="train", config=config)
        self._dataset_test = SpartanDataset(mode="test", config=config)
        self.load_dataset()

    def build_network(self):
        """
        Builds the DenseCorrespondenceNetwork
        :return:
        :rtype: DenseCorrespondenceNetwork
        """

        return DenseCorrespondenceNetwork.from_config(self._config['dense_correspondence_network'],
                                                      load_stored_params=False)

    def _construct_optimizer(self, parameters):
        """
        Constructs the optimizer
        :param parameters: Parameters to adjust in the optimizer
        :type parameters:
        :return: Adam Optimizer with params from the config
        :rtype: torch.optim
        """

        learning_rate = float(self._config['training']['learning_rate'])
        weight_decay = float(self._config['training']['weight_decay'])
        optimizer = optim.Adam(parameters, lr=learning_rate, weight_decay=weight_decay)
        return optimizer

    def _get_current_loss(self, logging_dict):
        """
        Gets the current loss for both test and train
        :return:
        :rtype: dict
        """
        d = dict()
        d['train'] = dict()
        d['test'] = dict()

        for key, val in d.iteritems():
            for field in logging_dict[key].keys():
                vec = logging_dict[key][field]

                if len(vec) > 0:
                    val[field] = vec[-1]
                else:
                    val[field] = -1 # placeholder


        return d

    def load_pretrained(self, model_folder, iteration=None):
        """
        Loads network and optimizer parameters from a previous training run.

        Note: It is up to the user to ensure that the model parameters match.
        e.g. width, height, descriptor dimension etc.
        :param model_folder: location of the folder containing the param files 001000.pth
        :type model_folder:
        :param iteration: which index to use, e.g. 3500, if None it loads the latest one
        :type iteration:
        :return:
        :rtype:
        """

        # find idx.pth and idx.pth.opt files
        if iteration is None:
            files = os.listdir(model_folder)
            model_param_file = sorted(fnmatch.filter(files, '*.pth'))[-1]
            optim_param_file = sorted(fnmatch.filter(files, '*.pth.opt'))[-1]

        else:
            prefix = utils.getPaddedString(iteration, width=6)
            model_param_file = prefix + ".pth"
            optim_param_file = prefix + ".pth.opt"

        print "model_param_file", model_param_file
        model_param_file = os.path.join(model_folder, model_param_file)
        optim_param_file = os.path.join(model_folder, optim_param_file)


        self._dcn = self.build_network()
        self._dcn.fcn.load_state_dict(torch.load(model_param_file))
        self._dcn.fcn.cuda()
        self._dcn.fcn.train()

        self._optimizer = self._construct_optimizer(self._dcn.parameters())
        self._optimizer.load_state_dict(torch.load(optim_param_file))


    def run(self, use_pretrained=False):
        """
        Runs the training
        :return:
        :rtype:
        """

        DCE = DenseCorrespondenceEvaluation

        self.setup()
        self.save_configs()

        if not use_pretrained:
            # create new network and optimizer
            self._dcn = self.build_network()
            self._optimizer = self._construct_optimizer(self._dcn.parameters())
        else:
            logging.info("using pretrained model")
            if (self._dcn is None):
                raise ValueError("you must set self._dcn if use_pretrained=True")
            if (self._optimizer is None):
                raise ValueError("you must set self._optimizer if use_pretrained=True")

        dcn = self._dcn
        optimizer = self._optimizer
        batch_size = self._data_loader.batch_size

        pixelwise_contrastive_loss = PixelwiseContrastiveLoss(config=self._config['loss_function'], image_shape=dcn.image_shape)
        pixelwise_contrastive_loss.debug = True

        loss = match_loss = non_match_loss = 0
        loss_current_iteration = 0



        max_num_iterations = self._config['training']['num_iterations']
        logging_rate = self._config['training']['logging_rate']
        save_rate = self._config['training']['save_rate']
        compute_test_loss_rate = self._config['training']['compute_test_loss_rate']

        # logging
        self._logging_dict = dict()
        self._logging_dict['train'] = {"iteration": [], "loss": [], "match_loss": [],
                                           "non_match_loss": [], "learning_rate": []}

        self._logging_dict['test'] = {"iteration": [], "loss": [], "match_loss": [],
                                           "non_match_loss": []}

        # save network before starting
        self.save_network(dcn, optimizer, 0)



        for epoch in range(50):  # loop over the dataset multiple times

            for i, data in enumerate(self._data_loader, 0):
                loss_current_iteration += 1
                start_iter = time.time()

                # get the inputs
                data_type, img_a, img_b, matches_a, matches_b, non_matches_a, non_matches_b, metadata = data
                data_type = data_type[0]

                if data_type == None:
                    print "\n didn't have any matches, continuing \n"
                    continue

                img_a = Variable(img_a.cuda(), requires_grad=False)
                img_b = Variable(img_b.cuda(), requires_grad=False)

                if data_type == "matches":
                    matches_a = Variable(matches_a.cuda().squeeze(0), requires_grad=False)
                    matches_b = Variable(matches_b.cuda().squeeze(0), requires_grad=False)
                    non_matches_a = Variable(non_matches_a.cuda().squeeze(0), requires_grad=False)
                    non_matches_b = Variable(non_matches_b.cuda().squeeze(0), requires_grad=False)

                optimizer.zero_grad()
                self.adjust_learning_rate(optimizer, loss_current_iteration)


                # run both images through the network
                image_a_pred = dcn.forward(img_a)
                image_a_pred = dcn.process_network_output(image_a_pred, batch_size)

                image_b_pred = dcn.forward(img_b)
                image_b_pred = dcn.process_network_output(image_b_pred, batch_size)

                # get loss
                if data_type == "matches":
                    loss, match_loss, non_match_loss =\
                        pixelwise_contrastive_loss.get_loss(image_a_pred,
                                                            image_b_pred,
                                                            matches_a,
                                                            matches_b,
                                                            non_matches_a,
                                                            non_matches_b)

                loss.backward()
                optimizer.step()

                elapsed = time.time() - start_iter

                print "single iteration took %.3f seconds" %(elapsed)


                def update_visdom_plots():
                    """
                    Updates the visdom plots with current loss function information
                    :return:
                    :rtype:
                    """
                    self._logging_dict['train']['iteration'].append(loss_current_iteration)
                    self._logging_dict['train']['loss'].append(loss.data[0])
                    self._logging_dict['train']['match_loss'].append(match_loss.data[0])
                    self._logging_dict['train']['non_match_loss'].append(non_match_loss.data[0])

                    learning_rate = DenseCorrespondenceTraining.get_learning_rate(optimizer)
                    self._logging_dict['train']['learning_rate'].append(learning_rate)

                    self._visdom_plots['train']['loss'].log(loss_current_iteration, loss.data[0])
                    self._visdom_plots['train']['match_loss'].log(loss_current_iteration, match_loss.data[0])
                    self._visdom_plots['train']['non_match_loss'].log(loss_current_iteration,
                                                             non_match_loss.data[0])

                    self._visdom_plots['learning_rate'].log(loss_current_iteration, learning_rate)


                    non_match_type = metadata['non_match_type'][0]
                    fraction_hard_negatives = pixelwise_contrastive_loss.debug_data['fraction_hard_negatives']

                    if pixelwise_contrastive_loss.debug:
                        if non_match_type == "masked":
                            self._visdom_plots['masked_hard_negative_rate'].log(loss_current_iteration, fraction_hard_negatives)
                        elif non_match_type == "non_masked":
                            self._visdom_plots['non_masked_hard_negative_rate'].log(loss_current_iteration,
                                                                                fraction_hard_negatives)
                        else:
                            raise ValueError("uknown non_match_type %s" %(non_match_type))



                def update_visdom_test_loss_plots(test_loss, test_match_loss, test_non_match_loss):
                    """
                    Log data about test loss and update the visdom plots
                    :return:
                    :rtype:
                    """

                    self._logging_dict['test']['loss'].append(test_loss)
                    self._logging_dict['test']['match_loss'].append(test_match_loss)
                    self._logging_dict['test']['non_match_loss'].append(test_non_match_loss)
                    self._logging_dict['test']['iteration'].append(loss_current_iteration)


                    self._visdom_plots['test']['loss'].log(loss_current_iteration, test_loss)
                    self._visdom_plots['test']['match_loss'].log(loss_current_iteration, test_match_loss)
                    self._visdom_plots['test']['non_match_loss'].log(loss_current_iteration, test_non_match_loss)



                update_visdom_plots()

                if loss_current_iteration % save_rate == 0:
                    self.save_network(dcn, optimizer, loss_current_iteration, logging_dict=self._logging_dict)

                if loss_current_iteration % logging_rate == 0:
                    logging.info("Training on iteration %d of %d" %(loss_current_iteration, max_num_iterations))

                    logging.info("single iteration took %.3f seconds" %(elapsed))

                    percent_complete = loss_current_iteration * 100.0/max_num_iterations
                    logging.info("Training is %d percent complete\n" %(percent_complete))


                if (loss_current_iteration % compute_test_loss_rate == 0):
                    logging.info("Computing test loss")
                    test_loss, test_match_loss, test_non_match_loss = DCE.compute_loss_on_dataset(dcn,
                                                                                                  self._data_loader_test, num_iterations=self._config['training']['test_loss_num_iterations'])

                    update_visdom_test_loss_plots(test_loss, test_match_loss, test_non_match_loss)

                if loss_current_iteration % self._config['training']['garbage_collect_rate'] == 0:
                    logging.debug("running garbage collection")
                    gc_start = time.time()
                    gc.collect()
                    gc_elapsed = time.time() - gc_start
                    logging.debug("garbage collection took %.2d seconds" %(gc_elapsed))

                if loss_current_iteration > max_num_iterations:
                    logging.info("Finished testing after %d iterations" % (max_num_iterations))
                    return


                # loss_history.append(loss.data[0])
                # match_loss_history.append(match_loss)
                # non_match_loss_history.append(non_match_loss)
                # loss_iteration_number_history.append(loss_current_iteration)

                # this is for testing


    def setup_logging_dir(self):
        """
        Sets up the directory where logs will be stored and config
        files written
        :return: full path of logging dir
        :rtype: str
        """

        if 'logging_dir_name' in self._config['training']:
            dir_name = self._config['training']['logging_dir_name']
        else:
            dir_name = utils.get_current_time_unique_name() +"_" + str(self._config['dense_correspondence_network']['descriptor_dimension']) + "d"

        self._logging_dir_name = dir_name

        self._logging_dir = os.path.join(utils.convert_to_absolute_path(self._config['training']['logging_dir']), dir_name)



        if os.path.isdir(self._logging_dir):
            shutil.rmtree(self._logging_dir)

        if not os.path.isdir(self._logging_dir):
            os.makedirs(self._logging_dir)

        return self._logging_dir

    def save_network(self, dcn, optimizer, iteration, logging_dict=None):
        """
        Saves network parameters to logging directory
        :return:
        :rtype: None
        """

        network_param_file = os.path.join(self._logging_dir, utils.getPaddedString(iteration, width=6) + ".pth")
        optimizer_param_file = network_param_file + ".opt"
        torch.save(dcn.state_dict(), network_param_file)
        torch.save(optimizer.state_dict(), optimizer_param_file)

        # also save loss history stuff
        if logging_dict is not None:
            log_history_file = os.path.join(self._logging_dir, utils.getPaddedString(iteration, width=6) + "_log_history.yaml")
            utils.saveToYaml(logging_dict, log_history_file)

            current_loss_file = os.path.join(self._logging_dir, 'loss.yaml')
            current_loss_data = self._get_current_loss(logging_dict)

            utils.saveToYaml(current_loss_data, current_loss_file)



    def save_configs(self):
        """
        Saves config files to the logging directory
        :return:
        :rtype: None
        """
        training_params_file = os.path.join(self._logging_dir, 'training.yaml')
        utils.saveToYaml(self._config, training_params_file)

        dataset_params_file = os.path.join(self._logging_dir, 'dataset.yaml')
        utils.saveToYaml(self._dataset.config, dataset_params_file)        

    def adjust_learning_rate(self, optimizer, iteration):
        """
        Adjusts the learning rate according to the schedule
        :param optimizer:
        :type optimizer:
        :param iteration:
        :type iteration:
        :return:
        :rtype:
        """

        steps_between_learning_rate_decay = self._config['training']['steps_between_learning_rate_decay']
        if iteration % steps_between_learning_rate_decay == 0:
            for param_group in optimizer.param_groups:
                param_group['lr'] = param_group['lr'] * 0.9

    @staticmethod
    def get_learning_rate(optimizer):
        for param_group in optimizer.param_groups:
            lr = param_group['lr']
            break

        return lr

    def setup_visdom(self):
        """
        Sets up visdom visualizer
        :return:
        :rtype:
        """
        self.start_visdom()
        self._visdom_env = self._logging_dir_name
        self._vis = visdom.Visdom(env=self._visdom_env)

        self._port = 8097
        self._visdom_plots = dict()

        self._visdom_plots["train"] = dict()
        self._visdom_plots['train']['loss'] = VisdomPlotLogger(
        'line', port=self._port, opts={'title': 'Train Loss'}, env=self._visdom_env)

        self._visdom_plots['learning_rate'] = VisdomPlotLogger(
        'line', port=self._port, opts={'title': 'Learning Rate'}, env=self._visdom_env)

        self._visdom_plots['train']['match_loss'] = VisdomPlotLogger(
        'line', port=self._port, opts={'title': 'Train Match Loss'}, env=self._visdom_env)

        self._visdom_plots['train']['non_match_loss'] = VisdomPlotLogger(
            'line', port=self._port, opts={'title': 'Train Non Match Loss'}, env=self._visdom_env)


        self._visdom_plots["test"] = dict()
        self._visdom_plots['test']['loss'] = VisdomPlotLogger(
            'line', port=self._port, opts={'title': 'Test Loss'}, env=self._visdom_env)

        self._visdom_plots['test']['match_loss'] = VisdomPlotLogger(
            'line', port=self._port, opts={'title': 'Test Match Loss'}, env=self._visdom_env)

        self._visdom_plots['test']['non_match_loss'] = VisdomPlotLogger(
            'line', port=self._port, opts={'title': 'Test Non Match Loss'}, env=self._visdom_env)

        self._visdom_plots['masked_hard_negative_rate'] = VisdomPlotLogger(
            'line', port=self._port, opts={'title': 'Masked Matches Hard Negative Rate'}, env=self._visdom_env)

        self._visdom_plots['non_masked_hard_negative_rate'] = VisdomPlotLogger(
            'line', port=self._port, opts={'title': 'Non-Masked Hard Negative Rate'}, env=self._visdom_env)


    @staticmethod
    def load_default_config():
        dc_source_dir = utils.getDenseCorrespondenceSourceDir()
        config_file = os.path.join(dc_source_dir, 'config', 'dense_correspondence',
                                   'training', 'training.yaml')

        config = utils.getDictFromYamlFilename(config_file)
        return config

    @staticmethod
    def make_default():
        return DenseCorrespondenceTraining()


    @staticmethod
    def start_visdom():
        """
        Starts visdom if it's not already running
        :return:
        :rtype:
        """

        vis = visdom.Visdom()

        if vis.check_connection():
            logging.info("Visdom already running, returning")
            return


        logging.info("Starting visdom")
        cmd = "python -m visdom.server"
        subprocess.Popen([cmd], shell=True)

