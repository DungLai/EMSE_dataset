from distutils.version import StrictVersion
import unittest
import numpy as np
from numpy.testing import assert_almost_equal
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.cluster import KMeans
from sklearn.pipeline import make_pipeline
import onnx
from onnxruntime import InferenceSession
from skl2onnx import convert_sklearn, to_onnx, wrap_as_onnx_mixin
from skl2onnx.common.data_types import FloatTensorType
from skl2onnx.algebra.onnx_ops import OnnxSub, OnnxDiv, OnnxClip, OnnxClip_6
from skl2onnx.algebra.onnx_operator_mixin import OnnxOperatorMixin
from test_utils import dump_data_and_model


class CustomOpTransformer(BaseEstimator, TransformerMixin,
                          OnnxOperatorMixin):

    def __init__(self):
        BaseEstimator.__init__(self)
        TransformerMixin.__init__(self)

    def fit(self, X, y=None):
        self.W_ = np.mean(X, axis=0)
        self.S_ = np.std(X, axis=0)
        return self

    def transform(self, X):
        return (X - self.W_) / self.S_

    def onnx_shape_calculator(self):
        def shape_calculator(operator):
            operator.outputs[0].type = operator.inputs[0].type
        return shape_calculator

    def to_onnx_operator(self, inputs=None, outputs=('Y', )):
        if inputs is None:
            raise RuntimeError("inputs should contain one name")
        i0 = self.get_inputs(inputs, 0)
        W = self.W_
        S = self.S_
        return OnnxDiv(OnnxSub(i0, W), S,
                       output_names=outputs)


class TestOnnxOperatorMixinSyntax(unittest.TestCase):

    def test_way1_convert_sklean(self):

        X = np.arange(20).reshape(10, 2)
        tr = KMeans(n_clusters=2)
        tr.fit(X)

        onx = convert_sklearn(
            tr, initial_types=[('X', FloatTensorType((None, X.shape[1])))])

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinWay1ConvertSklearn")

    def test_way2_to_onnx(self):

        X = np.arange(20).reshape(10, 2)
        tr = KMeans(n_clusters=2)
        tr.fit(X)

        onx = to_onnx(tr, X.astype(np.float32))

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinWay2ToOnnx")

    def test_way3_mixin(self):

        X = np.arange(20).reshape(10, 2)
        tr = KMeans(n_clusters=2)
        tr.fit(X)

        try:
            tr_mixin = wrap_as_onnx_mixin(tr)
        except KeyError as e:
            assert "SklearnGaussianProcessRegressor" in str(e)
            return

        try:
            onx = tr_mixin.to_onnx()
        except RuntimeError as e:
            assert "Method enumerate_initial_types" in str(e)
        onx = tr_mixin.to_onnx(X.astype(np.float32))

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinWay3OnnxMixin")

    def test_way4_mixin_fit(self):

        X = np.arange(20).reshape(10, 2)
        try:
            tr = wrap_as_onnx_mixin(KMeans(n_clusters=2))
        except KeyError as e:
            assert "SklearnGaussianProcessRegressor" in str(e)
            return
        tr.fit(X)

        onx = tr.to_onnx(X.astype(np.float32))

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinWay4OnnxMixin2")

    def test_pipe_way1_convert_sklean(self):

        X = np.arange(20).reshape(10, 2)
        tr = make_pipeline(CustomOpTransformer(), KMeans(n_clusters=2))
        tr.fit(X)

        onx = convert_sklearn(
            tr, initial_types=[('X', FloatTensorType((None, X.shape[1])))])

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinPipeWay1ConvertSklearn")

    def test_pipe_way2_to_onnx(self):

        X = np.arange(20).reshape(10, 2)
        tr = make_pipeline(CustomOpTransformer(), KMeans(n_clusters=2))
        tr.fit(X)

        onx = to_onnx(tr, X.astype(np.float32))

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinPipeWay2ToOnnx")

    def test_pipe_way3_mixin(self):

        X = np.arange(20).reshape(10, 2)
        tr = make_pipeline(CustomOpTransformer(), KMeans(n_clusters=2))
        tr.fit(X)

        try:
            tr_mixin = wrap_as_onnx_mixin(tr)
        except KeyError as e:
            assert "SklearnGaussianProcessRegressor" in str(e)
            return

        try:
            onx = tr_mixin.to_onnx()
        except RuntimeError as e:
            assert "Method enumerate_initial_types" in str(e)
        onx = tr_mixin.to_onnx(X.astype(np.float32))

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinPipeWay3OnnxMixin")

    def test_pipe_way4_mixin_fit(self):

        X = np.arange(20).reshape(10, 2)
        try:
            tr = wrap_as_onnx_mixin(make_pipeline(
                CustomOpTransformer(), KMeans(n_clusters=2)))
        except KeyError as e:
            assert "SklearnGaussianProcessRegressor" in str(e)
            return

        tr.fit(X)

        onx = tr.to_onnx(X.astype(np.float32))

        dump_data_and_model(
            X.astype(np.float32), tr, onx,
            basename="MixinPipeWay4OnnxMixin2")

    def common_test_onnxt_runtime_unary(self, onnx_cl, np_fct,
                                        op_version=None, debug=False):
        onx = onnx_cl('X', output_names=['Y'])
        X = np.array([[1, 2], [3, -4]], dtype=np.float64)
        model_def = onx.to_onnx(
            {'X': X.astype(np.float32)}, target_opset=op_version)
        if debug:
            print(model_def)
        try:
            oinf = InferenceSession(model_def.SerializeToString())
        except RuntimeError as e:
            if ("Could not find an implementation for the node "
                    "Cl_Clip:Clip(11)" in str(e)):
                # Not yet implemented in onnxruntime
                return
            raise e
        X = X.astype(np.float32)
        got = oinf.run(None, {'X': X})[0]
        assert_almost_equal(np_fct(X), got, decimal=6)

    @unittest.skipIf(
        StrictVersion(onnx.__version__) <= StrictVersion("1.5.0"),
        reason="Code working only with Clip(11) (onnx==1.6.0)")
    def test_onnx_clip(self):
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip(
                x, np.array([0], dtype=np.float32),
                output_names=output_names),
            lambda x: np.clip(x, 0, 1e5))
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip(
                x, np.array([-1000], dtype=np.float32),
                np.array([0], dtype=np.float32),
                output_names=output_names),
            lambda x: np.clip(x, -1e5, 0))
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip(
                x,
                np.array([0.1], dtype=np.float32),
                np.array([2.1], dtype=np.float32),
                output_names=output_names),
            lambda x: np.clip(x, 0.1, 2.1))

    def test_onnx_clip_10(self):
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip_6(
                x, min=1e-5, max=1e5, output_names=output_names,
                op_version=10),
            lambda x: np.clip(x, 1e-5, 1e5),
            op_version=10)
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip(
                x, min=1e-5, max=1e5, output_names=output_names,
                op_version=10),
            lambda x: np.clip(x, 1e-5, 1e5),
            op_version=10)
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip(
                x, max=1e-5, output_names=output_names,
                op_version=10),
            lambda x: np.clip(x, -1e5, 1e-5),
            op_version=10)
        self.common_test_onnxt_runtime_unary(
            lambda x, output_names=None: OnnxClip(
                x, min=0.1, max=2.1,
                output_names=output_names,
                op_version=10),
            lambda x: np.clip(x, 0.1, 2.1),
            op_version=10)


if __name__ == "__main__":
    unittest.main()
