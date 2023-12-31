# coding: utf-8
import logging
import os
import tensorflow as tf

# A prefix that will be prepended to the names in graph_def
PREFIX = "import"


def _load_frozen_graph(frozen_graph_file, device):
    """
    Load Frozen Graph

    Parameters
    ----------
    frozen_graph_file : str
        Full path to frozen graph (.pb file)
    device : str
        device type and id, (e.g. /cpu:0)

    Returns
    -------
    out : Graph :py:class:`tf.Graph`
    """
    logging.info("Loading frozen graph: {}".format(frozen_graph_file))
    with tf.device(device):
        with tf.gfile.GFile(frozen_graph_file, 'rb') as f:
            graph_def = tf.GraphDef()
            graph_def.ParseFromString(f.read())
        with tf.Graph().as_default() as graph:
            tf.import_graph_def(graph_def, name=PREFIX)
        return graph


def _get_input_and_output_names(graph):
    """
    Get input and output tensor names

    Parameters
    ----------
    graph : tf.Graph
        Tensorflow graph

    Returns
    -------
    input_tensor_names : List of input tensor names
    output_tensor_names  : List of output tensor names
    """
    input_tensor_names = []
    output_tensor_names = set()
    op_prefix = PREFIX + "/"
    for op in graph.get_operations():
        if not op.name.startswith(op_prefix):
            continue
        if op.type == 'Placeholder' and op.inputs.__len__() == 0 and op.outputs.__len__() == 1:
            input_tensor_names.append(op.outputs[0].name)
        if op.outputs.__len__() == 1:
            output_tensor_names.add(op.outputs[0].name)
    for op in graph.get_operations():
        for in_t in op.inputs:
            if in_t.name in output_tensor_names:
                output_tensor_names.remove(in_t.name)
    # Sort list of output tensor names in order to get consistent output in run()
    output_tensor_names = list(output_tensor_names)
    output_tensor_names.sort()
    return input_tensor_names, output_tensor_names


class TFModelImpl:
    """
    TFModelImpl is a wrapper on top of tensorflow which implements DLRModel API

    Parameters
    ----------
    frozen_graph_file : str
        Full path to frozen graph (.pb file)
    dev_type : str
        Optional. Device type ('cpu' or 'gpu')
    dev_id : int
        Optional. Device ID
    """
    def __init__(self, frozen_graph_file, dev_type=None, dev_id=None):
        if not os.path.exists(frozen_graph_file):
            raise ValueError("frozen_graph_file %s doesn't exist" % frozen_graph_file)
        self.frozen_graph_file = frozen_graph_file

        device = None
        if dev_type is not None:
            devices = ["cpu", "gpu"]
            if dev_type not in devices:
                raise ValueError("Invalid device type {}. Valid devices: {}".format(dev_type, devices))
            dev_id = 0 if dev_id is None else dev_id
            device = "/{}:{}".format(dev_type, dev_id)

        self.graph = _load_frozen_graph(frozen_graph_file, device)
        self.input_tensor_names, self.output_tensor_names = _get_input_and_output_names(self.graph)
        self.input_values = {}

    def _validate_input_name(self, name):
        if name not in self.input_tensor_names:
            raise ValueError(
                "Invalid input tensor name '{}'. List of input tensor names: {}".format(name, self.input_tensor_names))

    def _validate_input(self, input_values):
        if isinstance(input_values, dict):
            for k in input_values.keys():
                if not isinstance(k, str):
                    raise ValueError("input key must be string")
                self._validate_input_name(k)
        else:
            raise ValueError("input_values must be of type dict")

    def get_input_names(self):
        """
        Get all input names

        Returns
        -------
        out : list of :py:class:`str`
        """
        return self.input_tensor_names

    def get_output_names(self):
        """
        Get all output names

        Returns
        -------
        out : list of :py:class:`str`
        """
        return self.output_tensor_names

    def get_input(self, name, shape=None):
        """
        Get the current value of an input

        Parameters
        ----------
        name : str
            The name of an input
        shape : np.array (optional)
            If given, use as the shape of the returned array. Otherwise, the shape of
            the returned array will be inferred from the last call to set_input().
        """
        self._validate_input_name(name)
        if name not in self.input_values:
            return None
        out = self.input_values[name]
        if shape is not None:
            out = out.reshape(shape)
        return out

    def run(self, input_values):
        """
        Run inference with given input(s)

        Parameters
        ----------
        input_values : a dictionary where keys are input
            names (of type :py:class:`str`) and values are input tensors (of any type).
            Multiple inputs are allowed.

        Returns
        -------
        out : :py:class:`numpy.ndarray`
            Prediction result. Multiple outputs are possible.
        """
        self._validate_input(input_values)
        with tf.Session(graph=self.graph) as sess:
            feed_dict = {}
            for k, v in input_values.items():
                tensor = self.graph.get_tensor_by_name(k)
                feed_dict[tensor] = v
            output_tensors = []
            for k in self.output_tensor_names:
                tensor = self.graph.get_tensor_by_name(k)
                output_tensors.append(tensor)
            self.input_values = input_values

            out = sess.run(output_tensors, feed_dict=feed_dict)
            return out
