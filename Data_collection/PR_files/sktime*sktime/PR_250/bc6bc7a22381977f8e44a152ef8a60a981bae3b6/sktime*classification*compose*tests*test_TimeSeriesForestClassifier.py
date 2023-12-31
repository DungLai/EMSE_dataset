import numpy as np
import pytest
from sklearn.pipeline import FeatureUnion
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer
from sklearn.tree import DecisionTreeClassifier
from sktime.classification.compose import TimeSeriesForestClassifier
from sktime.datasets import load_gunpoint
from sktime.transformers.series_as_features.compose import RowTransformer
from sktime.transformers.series_as_features.segment import \
    RandomIntervalSegmenter
from sktime.transformers.series_as_features.summarize import \
    RandomIntervalFeatureExtractor
from sktime.utils.testing._series_as_features import \
    make_classification_problem
from sktime.utils.time_series import time_series_slope

X, y = make_classification_problem()
n_classes = len(np.unique(y))


# Check simple cases.
def test_predict_proba():
    clf = TimeSeriesForestClassifier(n_estimators=2)
    clf.fit(X, y)
    proba = clf.predict_proba(X)

    assert proba.shape == (X.shape[0], n_classes)
    np.testing.assert_array_equal(np.ones(X.shape[0]), np.sum(proba, axis=1))

    # test single row input
    y_proba = clf.predict_proba(X.iloc[[0], :])
    assert y_proba.shape == (1, n_classes)

    y_pred = clf.predict(X.iloc[[0], :])
    assert y_pred.shape == (1,)


# Compare results from different but equivalent implementations
@pytest.mark.parametrize("n_intervals", ['log', 1, 3])
@pytest.mark.parametrize("n_estimators", [1, 3])
def test_equivalent_model_specifications(n_intervals, n_estimators):
    random_state = 1234
    X_train, y_train = load_gunpoint(split="TRAIN", return_X_y=True)
    X_test, y_test = load_gunpoint(split="TEST", return_X_y=True)

    # Due to tie-breaking/floating point rounding in the final decision tree
    # classifier, the results depend on the
    # exact column order of the input data

    # Â Compare pipeline predictions outside of ensemble.
    steps = [
        ('segment', RandomIntervalSegmenter(n_intervals=n_intervals,
                                            random_state=random_state)),
        ('transform', FeatureUnion([
            ('mean', RowTransformer(
                FunctionTransformer(func=np.mean, validate=False))),
            ('std',
             RowTransformer(FunctionTransformer(func=np.std, validate=False))),
            ('slope', RowTransformer(
                FunctionTransformer(func=time_series_slope, validate=False)))
        ])),
        ('clf', DecisionTreeClassifier(random_state=random_state))
    ]
    clf1 = Pipeline(steps)
    clf1.fit(X_train, y_train)
    a = clf1.predict(X_test)

    steps = [
        ('transform', RandomIntervalFeatureExtractor(
            n_intervals=n_intervals,
            features=[np.mean, np.std,
                      time_series_slope],
            random_state=random_state)),
        ('clf', DecisionTreeClassifier(random_state=random_state))
    ]
    clf2 = Pipeline(steps)
    clf2.fit(X_train, y_train)
    b = clf2.predict(X_test)
    np.array_equal(a, b)


# Compare TimeSeriesForest ensemble predictions using pipeline as
# estimator
@pytest.mark.parametrize("n_intervals", ['sqrt', 1, 3])
@pytest.mark.parametrize("n_estimators", [1, 3])
def test_TimeSeriesForest_predictions(n_estimators, n_intervals):
    random_state = 1234
    X_train, y_train = load_gunpoint(split="TRAIN", return_X_y=True)
    X_test, y_test = load_gunpoint(split="TEST", return_X_y=True)

    features = [np.mean, np.std, time_series_slope]
    steps = [('transform',
              RandomIntervalFeatureExtractor(
                  random_state=random_state, features=features)),
             ('clf', DecisionTreeClassifier())]
    estimator = Pipeline(steps)

    clf1 = TimeSeriesForestClassifier(estimator=estimator,
                                      random_state=random_state,
                                      n_estimators=n_estimators)
    clf1.fit(X_train, y_train)
    a = clf1.predict_proba(X_test)

    # default, semi-modular implementation using
    # RandomIntervalFeatureExtractor internally
    clf2 = TimeSeriesForestClassifier(random_state=random_state,
                                      n_estimators=n_estimators)
    clf2.fit(X_train, y_train)
    b = clf2.predict_proba(X_test)

    np.testing.assert_array_equal(a, b)
