#!/usr/bin/env python

from __future__ import print_function

from keras.losses import categorical_crossentropy, logcosh
from keras.losses import binary_crossentropy
from keras.optimizers import SGD, Adam, Adadelta, Adagrad
from keras.optimizers import Adamax, RMSprop, Nadam
from keras.activations import softmax, relu, sigmoid

from sklearn.model_selection import train_test_split

from talos.scan.Scan import Scan
from talos.commands.reporting import Reporting

import talos as ta


p1 = {'lr': [1],
      'first_neuron': [4],
      'hidden_layers': [2],
      'batch_size': [50],
      'epochs': [1],
      'dropout': [0],
      'shapes': ['brick', 'funnel', 'triangle', 0.2],
      'optimizer': [Adam],
      'losses': [categorical_crossentropy],
      'activation': [relu],
      'last_activation': [softmax],
      'weight_regulizer': [None],
      'emb_output_dims': [None]}

p2 = {'lr': [1],
      'first_neuron': [4],
      'hidden_layers': [2],
      'batch_size': [50],
      'epochs': [1],
      'dropout': [0],
      'shapes': ['brick'],
      'optimizer': [Adam, Adagrad, Adamax, RMSprop, Adadelta, Nadam, SGD],
      'losses': [categorical_crossentropy],
      'activation': [relu],
      'last_activation': [softmax],
      'weight_regulizer': [None],
      'emb_output_dims': [None]}

p3 = {'lr': (0.5, 5, 10),
      'first_neuron': [4, 8, 16, 32, 64],
      'hidden_layers': [2, 3, 4, 5],
      'batch_size': (2, 30, 10),
      'epochs': [3],
      'dropout': (0, 0.5, 5),
      'weight_regulizer': [None],
      'shapes': ['funnel'],
      'emb_output_dims': [None],
      'optimizer': [Nadam],
      'losses': [logcosh, binary_crossentropy],
      'activation': [relu],
      'last_activation': [sigmoid]}

p4 = {'lr': [1],
      'first_neuron': [8, 24, 64],
      'hidden_layers': [2, 5, 10],
      'batch_size': [15, 30],
      'epochs': [1],
      'dropout': [0],
      'weight_regulizer': [None],
      'shapes': ['funnel'],
      'emb_output_dims': [None],
      'optimizer': [Nadam],
      'losses': [categorical_crossentropy],
      'activation': [relu],
      'last_activation': [sigmoid]}


class TestIris:

    def __init__(self):
        self.x, self.y = ta.templates.datasets.iris()
        self.x_train, self.x_dev, self.y_train, self.y_dev \
            = train_test_split(self.x, self.y, test_size=0.2)

    def test_scan_iris_1(self):
        print("Running Iris dataset test 1...")
        Scan(self.x, self.y, params=p1, dataset_name='testing',
             experiment_no='000', model=ta.templates.models.iris)

    def test_scan_iris_2(self):
        print("Running Iris dataset test 2...")
        Scan(self.x, self.y, params=p2, dataset_name='testing',
             experiment_no='000', model=ta.templates.models.iris,
             last_epoch_value=True)

    def test_scan_iris_3(self):
        print("Running Iris dataset test 3...")
        Scan(self.x, self.y, params=p4, dataset_name='testing',
             experiment_no='000', model=ta.templates.models.iris,
             premutation_filter=lambda p: p['first_neuron']*p['hidden_layers']<150,
             round_limit=4,
             last_epoch_value=True)

    def test_scan_iris_explicit_validation_set(self):
        print("Running explicit validation dataset test with metric reduction")
        Scan(self.x_train, self.y_train, params=p2,
             dataset_name='testing',
             experiment_no='000', model=ta.templates.models.iris,
             x_val=self.x_dev, y_val=self.y_dev)

    def test_scan_iris_explicit_validation_set_force_fail(self):
        print("Running explicit validation dataset test with loss reduction")
        try:
            Scan(self.x_train, self.y_train, params=p2,
                 dataset_name='testing',
                 experiment_no='000', model=ta.templates.models.iris,
                 y_val=self.y_dev)
        except RuntimeError:
            pass


class TestCancer:

    def __init__(self):
        self.x, self.y = ta.templates.datasets.cervical_cancer()
        self.model = ta.templates.models.cervical_cancer

    def test_scan_cancer_metric_reduction(self):
        print("Running Cervical Cancer dataset test...")
        Scan(self.x, self.y, grid_downsample=0.00025, params=p3,
             dataset_name='testing', experiment_no='a',
             model=self.model,
             random_method='latin_sudoku',
             reduction_threshold=0.01,
             reduction_method='correlation',
             reduction_interval=2)

    def test_scan_cancer_loss_reduction(self):
        print("Running Cervical Cancer dataset test...")
        Scan(self.x, self.y, grid_downsample=0.00025, params=p3,
             dataset_name='testing', experiment_no='a',
             model=self.model,
             random_method='sobol',
             reduction_metric='val_loss',
             reduction_threshold=0.01,
             reduction_method='correlation',
             reduction_interval=2)

    def test_linear_method(self):
        print("Testing linear method on Cancer dataset...")
        Scan(self.x, self.y, params=p3, dataset_name='testing',
             search_method='linear', grid_downsample=0.00025,
             experiment_no='000', model=self.model,
             random_method='quantum')

    def test_reverse_method(self):
        print("Testing reverse method on Cancer dataset...")
        Scan(self.x, self.y, params=p3, dataset_name='testing',
             search_method='reverse', grid_downsample=0.00025,
             experiment_no='000', model=self.model)


class TestReporting:

    def __init__(self):
        print("Testing Reporting...")

        r = Reporting('testing_000.csv')

        x = r.data
        x = r.correlate()
        x = r.high()
        x = r.low()
        x = r.rounds()
        x = r.rounds2high()
        x = r.best_params()
        x = r.plot_corr()
        x = r.plot_hist()
        x = r.plot_line()

        del x


class TestLoadDatasets:

    def __init__(self):
        print("Testing Load Datasets...")
        x = ta.templates.datasets.icu_mortality()
        x = ta.templates.datasets.icu_mortality(100)
        x = ta.templates.datasets.titanic()
        x = ta.templates.datasets.iris()
        x = ta.templates.datasets.cervical_cancer()
        x = ta.templates.datasets.breast_cancer()
        x = ta.templates.params.iris()
        x = ta.templates.params.breast_cancer()  # noqa
