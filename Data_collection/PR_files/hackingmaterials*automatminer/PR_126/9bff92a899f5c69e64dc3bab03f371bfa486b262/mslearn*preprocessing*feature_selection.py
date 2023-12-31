"""
Various in-house feature reduction techniques.
"""
import numpy as np
from sklearn.base import is_classifier
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier, \
    GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.model_selection import check_cv
from skrebate import MultiSURF

from mslearn.utils.package_tools import MatbenchError
from mslearn.base import LoggableMixin, DataframeTransformer

__authors__ = ["Alireza Faghaninia <alireza@lbl.gov>",
               "Alex Dunn <ardunn@lbl.gov>"]


class TreeBasedFeatureReduction(DataframeTransformer, LoggableMixin):
    """
    Tree-based feature reduction tools based on sklearn models that have
        the .feature_importances_ attribute.

    Args:
        mode (str): "regression" or "classification"
        importance_percentile (float): the selected percentile of the features
            sorted (descending) based on their importance.
        random_state (int): relevant if non-deterministic algorithms such as
            random forest are used.
        logger (Logger, bool): A custom logger object to use for logging.
            Alternatively, if set to True, the default mslearn logger will be
            used. If set to False, then no logging will occur.
    """
    def __init__(self, mode, importance_percentile=0.95,
                 logger=True, random_state=0):
        self._logger = self.get_logger(logger)
        self.mode = mode
        self.importance_percentile = importance_percentile
        self.selected_features = None
        self.rs = random_state

    def get_top_features(self, feat_importance):
        """
        Simple function to through a sorted list of features and select top
            percentiles.

        Args:
            feat_importance ([(str, float)]): a sorted list of
                (feature, importance) tuples

        Returns ([str]): list of the top * percentile of features. * determined
            by importance_percentile argument.

        """
        selected_feats = []
        frac = 0.0
        for feat in feat_importance:
            selected_feats.append(feat[0])
            frac += feat[1]
            if frac >= self.importance_percentile:
                break
        return selected_feats

    def get_reduced_features(self, tree_model, X, y, recursive=True):
        """
        Gives a reduced list of feature names given a tree-based model that
            has the .feature_importances_ attribute.

        Args:
            tree_model (instantiated sklearn tree-based model):
            X (pandas.dataframe):
            y (pandas.Series or numpy.ndarray): the target column
            recursive (bool):

        Returns ([str]): list of the top * percentile of features. * determined
            by importance_percentile argument.
        """
        m_curr = 0  # current number of top/important features
        m_prev = len(X.columns)
        while m_curr < m_prev:
            tree_model.fit(X, y)
            fimportance = sorted(zip(X.columns, tree_model.feature_importances_),
                                 key=lambda x: x[1], reverse=True)
            tfeats = self.get_top_features(fimportance)
            m_curr = len(tfeats)
            m_prev = len(X.columns)
            self.logger.debug('nfeatures: {}->{}'.format(
                len(X.columns), m_curr))
            X = X[tfeats]
            if not recursive:
                break
        return tfeats

    def fit(self, X, y, tree='rf', recursive=True, cv=5):
        """
        Fits to the data (X) and target (y) to determine the selected_features.

        Args:
            X (pandas.DataFrame): input data, note that numpy matrix is NOT
                accepted since the X.columns is used for feature names
            y (pandas.Series or np.ndarray): list of outputs used for fitting
                the tree model
            tree (str or instantiated sklearn tree-based model): if a model is
                directly fed, it must have the .feature_importances_ attribute
            recursive (bool): whether to recursively reduce the features (True)
                or just do it once (False)
            cv (int or CrossValidation): sklearn's cross-validation with the
                same options (int or actual instantiated CrossValidation)

        Returns (None):
            sets the class attribute .selected_features
        """
        m0 = len(X.columns)
        if isinstance(tree, str):
            if tree.lower() in ['rf', 'random forest', 'randomforest']:
                if self.mode.lower() in ['classification', 'classifier']:
                    tree = RandomForestClassifier(random_state=self.rs)
                else:
                    tree = RandomForestRegressor(random_state=self.rs)
            elif tree.lower() in ['gb', 'gbt', 'gradiet boosting']:
                if self.mode.lower() in ['classification', 'classifier']:
                    tree = GradientBoostingClassifier(random_state=self.rs)
                else:
                    tree = GradientBoostingRegressor(random_state=self.rs)
            else:
                raise MatbenchError('Unsupported tree_type {}!'.format(tree))

        cv = check_cv(cv=cv, y=y, classifier=is_classifier(tree))
        all_feats = []
        for train, test in cv.split(X, y, groups=None):
            Xtrn = X.iloc[train]
            ytrn = y.iloc[train]
            all_feats += self.get_reduced_features(tree, Xtrn, ytrn, recursive)
        # take the union of selected features of each fold
        self.selected_features = list(set(all_feats))
        self.logger.info(
            'Finished tree-based feature reduction of {} intial features to '
            '{}'.format(m0, len(self.selected_features)))
        return self

    def transform(self, X, y=None):
        """
        Transforms the data with the subset of features determined after
            calling the fit method on the data.

        Args:
            X (pandas.DataFrame): input data, note that numpy matrix is NOT
                accepted since the X.columns is used for feature names
            y (placeholder): ignored input (for consistency in notation)

        Returns (pandas.DataFrame): the data with reduced number of features.
        """
        if self.selected_features is None:
            raise MatbenchError('The fit method should be called first!')
        return X[self.selected_features]


def rebate(df, target, n_features):
    """
    Run the ReBATE relief algorithm on a dataframe, returning the reduced df.

    Args:
        df (pandas.DataFrame): A dataframe
        target (str): The target key (must be present in df)
        n_features (int): The number of features desired to be returned.

    Returns:

    """
    X = df.drop(target, axis=1)
    y = df[target]
    rf = MultiSURF(n_features_to_select=n_features, n_jobs=-1)
    matrix = rf.fit_transform(X.values, y.values)
    feats = []
    for c in matrix.T:
        for f in X.columns.values:
            if np.array_equal(c, X[f].values) and f not in feats:
                feats.append(f)
    return df[feats]