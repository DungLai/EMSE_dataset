from sktime.base import BaseEstimator

from sktime.utils import comparison
from sktime.utils.validation.series_as_features import validate_X


class BaseClassifier(BaseEstimator):
    """
    Base class for classifiers, for identification.
    """
    _estimator_type = "classifier"
    label_encoder = None
    random_state = None

    def fit(self, X, y):
        raise NotImplementedError("abstract method")

    def predict_proba(self, X):
        raise NotImplementedError("abstract method")

    def predict(self, X, input_checks=True):
        """
        classify instances
        ----
        Parameters
        ----
        X : panda dataframe
            instances of the dataset
        input_checks : boolean
            whether to verify the dataset (e.g. dimensions, etc)
        ----
        Returns
        ----
        predictions : 1d numpy array
            array of predictions of each instance (class value)
        """
        if input_checks:
            validate_X(X)
        distributions = self.predict_proba(X, input_checks=False)
        predictions = []
        for instance_index in range(0, X.shape[0]):
            distribution = distributions[instance_index]
            prediction = comparison.arg_max(distribution, self.random_state)
            predictions.append(prediction)
        predictions = self.label_encoder.inverse_transform(predictions)
        return predictions

    def score(self, X, y):
        from sklearn.metrics import accuracy_score
        return accuracy_score(y, self.predict(X), normalize=True)
