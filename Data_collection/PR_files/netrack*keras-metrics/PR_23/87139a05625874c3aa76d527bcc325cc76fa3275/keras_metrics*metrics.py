from functools import partial
from keras import backend as K
from keras.layers import Layer
from operator import truediv


class layer(Layer):

    def __init__(self, label=None, **kwargs):
        super(layer, self).__init__(**kwargs)
        self.stateful = True
        self.epsilon = K.constant(K.epsilon(), dtype="float64")

        # If layer metric is explicitly created to evaluate specified class,
        # then use a binary transformation of the output arrays, otherwise
        # calculate an "overall" metric.
        if label:
            self.cast_strategy = partial(self._binary, label=label)
        else:
            self.cast_strategy = self._categorical

    def cast(self, y_true, y_pred, dtype="int32"):
        """Convert the specified true and predicted output to the specified
        destination type (int32 by default).
        """
        return self.cast_strategy(y_true, y_pred, dtype=dtype)

    def _binary(self, y_true, y_pred, dtype, label=0):
        column = slice(label, label+1)

        # Slice a column of the output array.
        y_true = y_true[...,column]
        y_pred = y_pred[...,column]
        return self._categorical(y_true, y_pred, dtype)

    def _categorical(self, y_true, y_pred, dtype):
        # In case when user did not specify the label, and the shape
        # of the output vector has exactly two elements, we can choose
        # the label automatically.
        #
        # When the shape had dimension 3 and more and the label is
        # not specified, we should throw an error as long as calculated
        # metric is incorrect.
        labels = y_pred.shape[-1]
        if labels == 2:
            return self._binary(y_true, y_pred, dtype, label=1)
        elif labels > 2:
            raise ValueError("With 2 and more output classes a "
                             "metric label must be specified")

        y_true = K.cast(K.round(y_true), dtype)
        y_pred = K.cast(K.round(y_pred), dtype)
        return y_true, y_pred


class true_positive(layer):
    """Create a metric for model's true positives amount calculation.

    A true positive is an outcome where the model correctly predicts the
    positive class.
    """

    def __init__(self, name="true_positive", **kwargs):
        super(true_positive, self).__init__(name=name, **kwargs)
        self.tp = K.variable(0, dtype="int32")

    def reset_states(self):
        """Reset the state of the metric."""
        K.set_value(self.tp, 0)

    def __call__(self, y_true, y_pred):
        y_true, y_pred = self.cast(y_true, y_pred)

        tp = K.sum(y_true * y_pred)
        current_tp = self.tp * 1

        tp_update = K.update_add(self.tp, tp)
        self.add_update(tp_update, inputs=[y_true, y_pred])

        return tp + current_tp


class true_negative(layer):
    """Create a metric for model's true negatives amount calculation.

    A true negative is an outcome where the model correctly predicts the
    negative class.
    """

    def __init__(self, name="true_negative", **kwargs):
        super(true_negative, self).__init__(name=name, **kwargs)
        self.tn = K.variable(0, dtype="int32")

    def reset_states(self):
        """Reset the state of the metric."""
        K.set_value(self.tn, 0)

    def __call__(self, y_true, y_pred):
        y_true, y_pred = self.cast(y_true, y_pred)

        neg_y_true = 1 - y_true
        neg_y_pred = 1 - y_pred

        tn = K.sum(neg_y_true * neg_y_pred)
        current_tn = self.tn * 1

        tn_update = K.update_add(self.tn, tn)
        self.add_update(tn_update, inputs=[y_true, y_pred])

        return tn + current_tn


class false_negative(layer):
    """Create a metric for model's false negatives amount calculation.

    A false negative is an outcome where the model incorrectly predicts the
    negative class.
    """

    def __init__(self, name="false_negative", **kwargs):
        super(false_negative, self).__init__(name=name, **kwargs)
        self.fn = K.variable(0, dtype="int32")

    def reset_states(self):
        """Reset the state of the metric."""
        K.set_value(self.fn, 0)

    def __call__(self, y_true, y_pred):
        y_true, y_pred = self.cast(y_true, y_pred)
        neg_y_pred = 1 - y_pred

        fn = K.sum(y_true * neg_y_pred)
        current_fn = self.fn * 1

        fn_update = K.update_add(self.fn, fn)
        self.add_update(fn_update, inputs=[y_true, y_pred])

        return fn + current_fn


class false_positive(layer):
    """Create a metric for model's false positive amount calculation.

    A false positive is an outcome where the model incorrectly predicts the
    positive class.
    """

    def __init__(self, name="false_positive", **kwargs):
        super(false_positive, self).__init__(name=name, **kwargs)
        self.fp = K.variable(0, dtype="int32")

    def reset_states(self):
        """Reset the state of the metric."""
        K.set_value(self.fp, 0)

    def __call__(self, y_true, y_pred):
        y_true, y_pred = self.cast(y_true, y_pred)
        neg_y_true = 1 - y_true

        fp = K.sum(neg_y_true * y_pred)
        current_fp = self.fp * 1

        fp_update = K.update_add(self.fp, fp)
        self.add_update(fp_update, inputs=[y_true, y_pred])

        return fp + current_fp


class recall(layer):
    """Create a metric for model's recall calculation.

    Recall measures proportion of actual positives that was identified correctly.
    """

    def __init__(self, name="recall", **kwargs):
        super(recall, self).__init__(name=name, **kwargs)

        self.tp = true_positive()
        self.fn = false_negative()

    def reset_states(self):
        """Reset the state of the metrics."""
        self.tp.reset_states()
        self.fn.reset_states()

    def __call__(self, y_true, y_pred):
        tp = self.tp(y_true, y_pred)
        fn = self.fn(y_true, y_pred)

        self.add_update(self.tp.updates)
        self.add_update(self.fn.updates)

        tp = K.cast(tp, self.epsilon.dtype)
        fn = K.cast(fn, self.epsilon.dtype)

        return truediv(tp, tp + fn + self.epsilon)


class precision(layer):
    """Create  a metric for model's precision calculation.

    Precision measures proportion of positives identifications that were
    actually correct.
    """

    def __init__(self, name="precision", **kwargs):
        super(precision, self).__init__(name=name, **kwargs)

        self.tp = true_positive()
        self.fp = false_positive()

    def reset_states(self):
        """Reset the state of the metrics."""
        self.tp.reset_states()
        self.fp.reset_states()

    def __call__(self, y_true, y_pred):
        tp = self.tp(y_true, y_pred)
        fp = self.fp(y_true, y_pred)

        self.add_update(self.tp.updates)
        self.add_update(self.fp.updates)

        tp = K.cast(tp, self.epsilon.dtype)
        fp = K.cast(fp, self.epsilon.dtype)

        return truediv(tp, tp + fp + self.epsilon)


class f1_score(layer):
    """Create a metric for the model's F1 score calculation.

    The F1 score is the harmonic mean of precision and recall.
    """

    def __init__(self, name="f1_score", label=None, **kwargs):
        super(f1_score, self).__init__(name=name, label=label, **kwargs)

        self.precision = precision(label=label)
        self.recall = recall(label=label)

    def reset_states(self):
        """Reset the state of the metrics."""
        self.precision.reset_states()
        self.recall.reset_states()

    def __call__(self, y_true, y_pred):
        pr = self.precision(y_true, y_pred)
        rec = self.recall(y_true, y_pred)

        self.add_update(self.precision.updates)
        self.add_update(self.recall.updates)

        return 2 * truediv(pr * rec, pr + rec + K.epsilon())
