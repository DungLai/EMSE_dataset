# SPDX-License-Identifier: MIT
# Copyright (c) 2019 Intel Corporation
"""
Base class for Scikit models
"""
import os
import json
import math
import hashlib
from pathlib import Path
from typing import AsyncIterator, Tuple, Any, NamedTuple

import joblib
import numpy as np
import pandas as pd

from dffml.repo import Repo
from dffml.source.source import Sources
from dffml.accuracy import Accuracy
from dffml.model.model import ModelConfig, ModelContext, Model, ModelNotTrained
from dffml.feature.feature import Features, Feature


class ScikitConfig(ModelConfig, NamedTuple):
    directory: str
    predict: Feature
    features: Features


class ScikitContext(ModelContext):
    def __init__(self, parent):
        super().__init__(parent)
        self.features = self.applicable_features(self.parent.config.features)
        self._features_hash = self._feature_predict_hash()
        self.clf = None

    @property
    def confidence(self):
        return self.parent.saved.get(self._features_hash, float("nan"))

    @confidence.setter
    def confidence(self, confidence):
        self.parent.saved[self._features_hash] = confidence

    def _feature_predict_hash(self):
        return hashlib.sha384(
            "".join(self.features + [self.parent.config.predict.NAME]).encode()
        ).hexdigest()

    def _filename(self):
        return os.path.join(
            self.parent.config.directory, self._features_hash + ".joblib"
        )

    async def __aenter__(self):
        if os.path.isfile(self._filename()):
            self.clf = joblib.load(self._filename())
        else:
            config = self.parent.config._asdict()
            del config["directory"]
            del config["predict"]
            del config["features"]
            self.clf = self.parent.SCIKIT_MODEL(**config)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    async def train(self, sources: Sources):
        data = []
        async for repo in sources.with_features(
            self.features + [self.parent.config.predict.NAME]
        ):
            feature_data = repo.features(
                self.features + [self.parent.config.predict.NAME]
            )
            data.append(feature_data)
        df = pd.DataFrame(data)
        xdata = np.array(df.drop([self.parent.config.predict.NAME], 1))
        ydata = np.array(df[self.parent.config.predict.NAME])
        self.logger.info("Number of input repos: {}".format(len(xdata)))
        self.clf.fit(xdata, ydata)
        joblib.dump(self.clf, self._filename())

    async def accuracy(self, sources: Sources) -> Accuracy:
        if not os.path.isfile(self._filename()):
            raise ModelNotTrained("Train model before assessing for accuracy.")
        data = []
        async for repo in sources.with_features(self.features):
            feature_data = repo.features(
                self.features + [self.parent.config.predict.NAME]
            )
            data.append(feature_data)
        df = pd.DataFrame(data)
        xdata = np.array(df.drop([self.parent.config.predict.NAME], 1))
        ydata = np.array(df[self.parent.config.predict.NAME])
        self.logger.debug("Number of input repos: {}".format(len(xdata)))
        self.confidence = self.clf.score(xdata, ydata)
        self.logger.debug("Model Accuracy: {}".format(self.confidence))
        return self.confidence

    async def predict(
        self, repos: AsyncIterator[Repo]
    ) -> AsyncIterator[Tuple[Repo, Any, float]]:
        if not os.path.isfile(self._filename()):
            raise ModelNotTrained("Train model before prediction.")
        async for repo in repos:
            feature_data = repo.features(self.features)
            df = pd.DataFrame(feature_data, index=[0])
            predict = np.array(df)
            self.logger.debug(
                "Predicted Value of {} for {}: {}".format(
                    self.parent.config.predict,
                    predict,
                    self.clf.predict(predict),
                )
            )
            repo.predicted(self.clf.predict(predict)[0], self.confidence)
            yield repo


class ScikitContextUnsprvised(ScikitContext):
    def __init__(self, parent):
        super().__init__(parent)

    def _feature_predict_hash(self):
        return hashlib.sha384("".join(self.features).encode()).hexdigest()

    async def __aenter__(self):
        if os.path.isfile(self._filename()):
            self.clf = joblib.load(self._filename())
        else:
            config = self.parent.config._asdict()
            del config["directory"]
            del config["features"]
            self.clf = self.parent.SCIKIT_MODEL(**config)
        return self

    async def train(self, sources: Sources):
        data = []
        async for repo in sources.with_features(self.features):
            feature_data = repo.features(self.features)
            data.append(feature_data)
        df = pd.DataFrame(data)
        xdata = np.array(df)
        self.logger.info("Number of input repos: {}".format(len(xdata)))
        self.clf.fit(xdata)
        joblib.dump(self.clf, self._filename())

    async def accuracy(self, sources: Sources) -> Accuracy:
        if not os.path.isfile(self._filename()):
            raise ModelNotTrained("Train model before assessing for accuracy.")
        data = []
        async for repo in sources.with_features(self.features):
            feature_data = repo.features(self.features)
            data.append(feature_data)
        df = pd.DataFrame(data)
        xdata = np.array(df)
        self.logger.debug("Number of input repos: {}".format(len(xdata)))
        self.confidence = self.clf.score(xdata)
        self.logger.debug("Model Accuracy: {}".format(self.confidence))
        return self.confidence

    async def predict(
        self, repos: AsyncIterator[Repo]
    ) -> AsyncIterator[Tuple[Repo, Any, float]]:
        if not os.path.isfile(self._filename()):
            raise ModelNotTrained("Train model before prediction.")
        async for repo in repos:
            feature_data = repo.features(self.features)
            df = pd.DataFrame(feature_data, index=[0])
            predict = np.array(df)
            self.logger.debug(
                "Predicted cluster for {}: {}".format(
                    predict, self.clf.predict(predict),
                )
            )
            repo.predicted(self.clf.predict(predict)[0], self.confidence)
            yield repo


class Scikit(Model):
    def __init__(self, config) -> None:
        super().__init__(config)
        self.saved = {}

    def _filename(self):
        return os.path.join(
            self.config.directory,
            hashlib.sha384(self.config.predict.NAME.encode()).hexdigest()
            + ".json",
        )

    async def __aenter__(self) -> "Scikit":
        path = Path(self._filename())
        if path.is_file():
            self.saved = json.loads(path.read_text())
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        Path(self._filename()).write_text(json.dumps(self.saved))


class ScikitUnsprvised(Scikit):
    def __init__(self, config) -> None:
        super().__init__(config)

    def _filename(self):
        print("--------------------------------------------")
        print(self)
        print("---------------------------------------------")
        return os.path.join(
            self.config.directory,
            hashlib.sha384(
                (
                    "".join(sorted(feature.NAME for feature in self.config.features))
                ).encode()
            ).hexdigest()
            + ".json",
        )
