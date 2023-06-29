# SPDX-License-Identifier: MIT
# Copyright (c) 2019 Intel Corporation
'''
Description of what this model does
'''
import os
import abc
from typing import AsyncIterator, Tuple, Any, List, Optional, NamedTuple, Dict
from statistics import mean
import numpy as np

from dffml.repo import Repo
from dffml.source.source import Sources
from dffml.feature import Features
from dffml.accuracy import Accuracy
from dffml.model.model import ModelConfig, ModelContext, Model
from dffml.util.entrypoint import entry_point
from dffml.util.cli.arg import Arg


class SLRConfig(ModelConfig, NamedTuple):
    predict: str
    directory: str


class SLRContext(ModelContext):
    '''
    Model wraping scratch API
    '''
    def __init__(self, parent):
        super().__init__(parent)
        self.xData = np.array([0.0])
        self.yData = np.array([0.0])
        self.regression_line = None

    async def squared_error(self, ys, yline):
        return sum((ys - yline)**2)

    async def coeff_of_deter(self, ys, regression_line):
        y_mean_line = [mean(ys) for y in ys]
        squared_error_mean = await self.squared_error(ys, y_mean_line)
        squared_error_regression = await self.squared_error(ys, regression_line)
        return 1 - (squared_error_regression/squared_error_mean)

    async def applicable_features(self, features: Features):
        usable = []
        if len(features) != 1:
            raise ValueError("Simple Linear Regression doesn't support features other than 1")
        for feature in features:
            if feature.dtype() != int and feature.dtype() != float:
                raise ValueError("Simple Linear Regression only supports int or float feature")
            if feature.length() != 1:
                raise ValueError("Simple LR only supports single values (non-matrix / array)")
            usable.append(feature.NAME)
        return usable

    async def best_fit_line(self, xs, ys):
        # This causes an error, xs and ys are regular python lists at this point
        # xs = [1.1, 1.3, 1.5, 2.0, 2.2, 2.9, 3.0, 3.2, 3.2, 3.7, 3.9, 4.0, 4.0, 4.1, 4.5, 4.9, 5.1, 5.3, 5.9, 6.0, 6.8, 7.1, 7.9, 8.2, 8.7, 9.0, 9.5, 9.6, 10.3, 10.5]
        # ys = [42393.0, 49255.0, 40781.0, 46575.0, 42941.0, 59692.0, 63200.0, 57495.0, 67495.0, 60239.0, 66268.0, 58844.0, 60007.0, 60131.0, 64161.0, 70988.0, 69079.0, 86138.0, 84413.0, 96990.0, 94788.0, 101323.0, 104352.0, 116862.0, 112481.0, 108632.0, 120019.0, 115685.0, 125441.0, 124922.0]
        m = ((mean(xs)*mean(ys)) - mean(xs*ys))/((mean(xs)*mean(xs)) - (mean(xs*xs)))
        b = mean(ys) - (m*mean(xs))
        regression_line = [m*x + b for x in xs]
        accuracy = await self.coeff_of_deter(ys, regression_line)
        return (m, b, accuracy)

    async def train(self, sources: Sources, features: Features):
        '''
        Train using repos as the data to learn from.
        '''
        feature = await self.applicable_features(features)
        async for repo in sources.with_features(feature):
            # Grab a subset of the feature data being stored within the repo
            # The subset is the feature_we_care_about and the feature we are want to predict
            feature_data = repo.features(feature + [self.parent.config.predict])
            self.xData = np.append(self.xData, feature_data[feature[0]])
            self.yData = np.append(self.yData, feature_data[self.parent.config.predict])
        self.regression_line = await self.best_fit_line(self.xData, self.yData)
        
    async def accuracy(self, sources: Sources, features: Features) -> Accuracy:
        '''
        Evaluates the accuracy of our model after training using the input repos
        as test data.
        '''
        if self.regression_line is None:
            raise ValueError('Model Not Trained')
        accuracy_value = self.regression_line[2]
        return Accuracy(accuracy_value)

    async def predict(self, repos: AsyncIterator[Repo], features: Features) -> \
                    AsyncIterator[Tuple[Repo, Any, float]]:
        '''
        Uses trained data to make a prediction about the quality of a repo.
        '''
        async for repo in repos:
            yield repo, classifications[0], 1.0


@entry_point('slr')
class SLR(Model):

    CONTEXT = SLRContext

    @classmethod
    def args(cls, args, *above) -> Dict[str, Arg]:
        cls.config_set(args, above, 'directory', Arg(
            default=os.path.join(os.path.expanduser('~'), '.cache', 'dffml',
                                 'scratch')))
        cls.config_set(args, above, 'predict', Arg(type=str))
        return args

    @classmethod
    def config(cls, config, *above) -> 'SLRConfig':
        return SLRConfig(
            directory=cls.config_get(config, above, 'directory'),
            predict=cls.config_get(config, above, 'predict'),
        )