"""
Test scikit-learn's PowerTransform
"""
import unittest

import numpy as np

from skl2onnx import convert_sklearn
from skl2onnx.common.data_types import FloatTensorType
from test_utils import dump_data_and_model

try:
    from sklearn.preprocessing import PowerTransformer  # noga
except ImportError:
    # Not available in scikit-learn < 0.20.0
    PowerTransformer = None


class TestSklearnPowerTransformer(unittest.TestCase):
    """Test cases for PowerTransform converter"""
    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_yeo_johnson_positive_without_scaler(self):
        pt = PowerTransformer(standardize=False)
        data = np.array([[1, 2], [3, 2], [4, 5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_yeo_johnson_negative_without_scaler(self):
        pt = PowerTransformer(standardize=False)
        data = np.array([[-1, -2], [-3, -2], [-4, -5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_yeo_johnson_combined_without_scaler(self):
        pt = PowerTransformer(standardize=False)
        data = np.array([[1, -2], [0, -2], [-4, 5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_box_cox_without_scaler(self):
        pt = PowerTransformer(standardize=False, method='box-cox')
        data = np.array([[1, 2], [3, 2], [4, 5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_yeo_johnson_positive_with_scaler(self):
        pt = PowerTransformer()
        data = np.array([[1, 2], [3, 2], [4, 5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_yeo_johnson_negative_with_scaler(self):
        pt = PowerTransformer()
        data = np.array([[-1, -2], [-3, -2], [-4, -5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_yeo_johnson_combined_with_scaler(self):
        pt = PowerTransformer()
        data = np.array([[1, -2], [3, -2], [-4, 5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_box_cox_with_scaler(self):
        pt = PowerTransformer(method='box-cox')
        data = np.array([[1, 2], [3, 2], [4, 5]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")

    @unittest.skipIf(PowerTransformer is None, "Problems with import occurred")
    def test_powertransformer_zeros(self):
        pt = PowerTransformer()
        data = np.array([[0, 0], [0, 0]], dtype=np.float32)
        model = pt.fit(data)
        model_onnx = convert_sklearn(model, "scikit-learn PowerTransformer",
                                     [("input_float",
                                       FloatTensorType([data.shape[0],
                                                        data.shape[1]]))])
        self.assertIsNotNone(model_onnx)
        dump_data_and_model(data, model, model_onnx,
                            basename="PowerTransformer")


if __name__ == '__main__':
    unittest.main()
