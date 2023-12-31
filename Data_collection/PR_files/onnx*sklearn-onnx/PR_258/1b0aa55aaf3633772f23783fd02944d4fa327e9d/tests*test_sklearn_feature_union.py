# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------

import unittest
import numpy as np
from sklearn.datasets import load_digits, load_iris
from sklearn.decomposition import PCA, TruncatedSVD
from sklearn.model_selection import train_test_split
from sklearn.pipeline import FeatureUnion
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType, Int64TensorType
from test_utils import dump_data_and_model


class TestSklearnAdaBoostModels(unittest.TestCase):
    def test_feature_union_default(self):
        data = load_iris()
        X, y = data.data, data.target
        X = X.astype(np.float32)
        X_train, X_test, *_ = train_test_split(X, y, test_size=0.5,
                                               random_state=42)
        model = FeatureUnion([('standard', StandardScaler()),
                              ('minmax', MinMaxScaler())]).fit(X_train)
        model_onnx = convert_sklearn(
            model, 'feature union', [('input', FloatTensorType(X_test.shape))])
        self.assertTrue(model_onnx is not None)
        dump_data_and_model(X_test,
                            model,
                            model_onnx,
                            basename="SklearnFeatureUnionDefault")

    def test_feature_union_transformer_weights_0(self):
        data = load_iris()
        X, y = data.data, data.target
        X = X.astype(np.float32)
        X_train, X_test, *_ = train_test_split(X, y, test_size=0.5,
                                               random_state=42)
        model = FeatureUnion([('standard', StandardScaler()),
                              ('minmax', MinMaxScaler())],
                             transformer_weights={'standard': 2, 'minmax': 4}
                             ).fit(X_train)
        model_onnx = convert_sklearn(
            model, 'feature union', [('input', FloatTensorType(X_test.shape))])
        self.assertTrue(model_onnx is not None)
        dump_data_and_model(X_test,
                            model,
                            model_onnx,
                            basename="SklearnFeatureUnionTransformerWeights0")

    def test_feature_union_transformer_weights_1(self):
        data = load_digits()
        X, y = data.data, data.target
        X = X.astype(np.int64)
        X_train, X_test, *_ = train_test_split(X, y, test_size=0.5,
                                               random_state=42)
        model = FeatureUnion([('pca', PCA()),
                              ('svd', TruncatedSVD())],
                             transformer_weights={'pca': 10, 'svd': 3}
                             ).fit(X_train)
        model_onnx = convert_sklearn(
            model, 'feature union', [('input', Int64TensorType(X_test.shape))])
        self.assertTrue(model_onnx is not None)
        dump_data_and_model(
            X_test,
            model,
            model_onnx,
            basename="SklearnFeatureUnionTransformerWeights1-Dec4",
            allow_failure="StrictVersion("
            "onnxruntime.__version__)"
            "<= StrictVersion('0.2.1')",
        )

    def test_feature_union_transformer_weights_2(self):
        data = load_digits()
        X, y = data.data, data.target
        X = X.astype(np.float32)
        X_train, X_test, *_ = train_test_split(X, y, test_size=0.5,
                                               random_state=42)
        model = FeatureUnion([('pca', PCA()),
                              ('svd', TruncatedSVD())],
                             transformer_weights={'pca1': 10, 'svd2': 3}
                             ).fit(X_train)
        model_onnx = convert_sklearn(
            model, 'feature union', [('input', FloatTensorType(X_test.shape))])
        self.assertTrue(model_onnx is not None)
        dump_data_and_model(
            X_test,
            model,
            model_onnx,
            basename="SklearnFeatureUnionTransformerWeights2-Dec4",
            allow_failure="StrictVersion("
            "onnxruntime.__version__)"
            "<= StrictVersion('0.2.1')",
        )


if __name__ == "__main__":
    unittest.main()
