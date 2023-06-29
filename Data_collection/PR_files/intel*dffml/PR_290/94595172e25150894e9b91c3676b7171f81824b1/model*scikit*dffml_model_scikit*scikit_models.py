# SPDX-License-Identifier: MIT
# Copyright (c) 2019 Intel Corporation
"""
Description of what this model does
"""
import os
import sys
import ast
import inspect
import dataclasses
from collections import namedtuple
from typing import Dict, Optional, Tuple, Type, Any

from sklearn.neural_network import MLPClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.gaussian_process import (
    GaussianProcessClassifier,
    GaussianProcessRegressor,
)
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor
from sklearn.ensemble import (
    RandomForestClassifier,
    AdaBoostClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    BaggingClassifier,
)
from sklearn.naive_bayes import GaussianNB, BernoulliNB, MultinomialNB
from sklearn.discriminant_analysis import (
    QuadraticDiscriminantAnalysis,
    LinearDiscriminantAnalysis,
)
from sklearn.linear_model import (
    LinearRegression,
    LogisticRegression,
    ElasticNet,
    BayesianRidge,
    Lasso,
    ARDRegression,
    RANSACRegressor,
    OrthogonalMatchingPursuit,
    Lars,
    Ridge,
)
from sklearn.cluster import KMeans

from dffml.base import make_config, field
from dffml.util.cli.arg import Arg
from dffml.util.entrypoint import entry_point
from dffml_model_scikit.scikit_base import (
    Scikit,
    ScikitContext,
    ScikitUnsprvised,
    ScikitContextUnsprvised,
)

from dffml.feature.feature import Feature, Features
from dffml.util.cli.parser import list_action


def applicable_features(self, features):
    usable = []
    for feature in features:
        if feature.dtype() != int and feature.dtype() != float:
            raise ValueError("Models only supports int or float feature")
        if feature.length() != 1:
            raise ValueError(
                "Models only supports single values (non-matrix / array)"
            )
        usable.append(feature.NAME)
    return sorted(usable)


# TODO modify config_get to raise an error if NoDefaultValue would be the return
# value of config_get
class NoDefaultValue:
    pass


class ParameterNotInDocString(Exception):
    """
    Raised when a scikit class has a parameter in its ``__init__`` which was not
    present in it's docstring. Therefore we have no typing information for it.
    """


def scikit_get_default(type_str):
    if not "default" in type_str:
        return dataclasses.MISSING
    type_str = type_str[type_str.index("default") :]
    type_str = type_str.replace("default", "")
    type_str = type_str.replace(")", "")
    type_str = type_str.replace("=", "")
    type_str = type_str.replace('"', "")
    type_str = type_str.replace("'", "")
    type_str = type_str.strip()
    if type_str == "None":
        return None
    return type_str


SCIKIT_DOCS_TYPE_MAP = {
    "int": int,
    "integer": int,
    "str": str,
    "string": str,
    "float": float,
    "dict": dict,
    "bool": bool,
}


def scikit_doc_to_field(type_str, param):
    default = param.default
    if default is inspect.Parameter.empty:
        default = scikit_get_default(type_str)

    type_cls = Any

    # Set of choices
    if "{'" in type_str and "'}" in type_str:
        type_cls = str
    elif "{" in type_str and "}" in type_str:
        type_cls = int
        if "." in type_str:
            type_cls = float
    else:
        type_split = list(
            map(lambda x: x.lower(), type_str.replace(",", "").split())
        )
        for scikit_type_name, python_type in SCIKIT_DOCS_TYPE_MAP.items():
            if scikit_type_name in type_split:
                type_cls = python_type

    if type_cls == Any and default != None:
        type_cls = type(default)

    return type_cls, field(type_str, default=default)


def mkscikit_config_cls(
    name: str,
    cls: Type,
    properties: Optional[Dict[str, Tuple[Type, field]]] = None,
):
    """
    Given a scikit class, read its docstring and ``__init__`` parameters to
    generate a config class with properties containing the correct types,
    and default values.
    """
    if properties is None:
        properties = {}

    parameters = inspect.signature(cls).parameters
    docstring = inspect.getdoc(cls)
    docparams = {}

    # Parse parameters and their datatypes from docstring
    last_param_name = None
    for line in docstring.split("\n"):
        if not ":" in line:
            continue
        param_name, dtypes = line.split(":", maxsplit=1)
        param_name = param_name.strip()
        dtypes = dtypes.strip()
        if not param_name in parameters or param_name in docparams:
            continue
        docparams[param_name] = dtypes
        last_param_name = param_name

    # Ensure all required parameters are present in docstring
    for param_name, param in parameters.items():
        if param_name in ["args", "kwargs"]:
            continue
        if not param_name in docparams:
            raise ParameterNotInDocString(
                f"{param_name} for {cls.__qualname__}"
            )
        properties[param_name] = scikit_doc_to_field(
            docparams[param_name], param
        )

    return make_config(
        name, [tuple([key] + list(value)) for key, value in properties.items()]
    )


# {'clsf':"CLASSIFICATION","reg":"REGRESSION","clstr":"CLUSTERING"}
for entry_point_name, name, cls, applicable_features_function, algo_type in [
    (
        "scikitknn",
        "KNeighborsClassifier",
        KNeighborsClassifier,
        applicable_features,
        "clsf",
    ),
    (
        "scikitadaboost",
        "AdaBoostClassifier",
        AdaBoostClassifier,
        applicable_features,
        "clsf",
    ),
    ("scikitsvc", "SVC", SVC, applicable_features, "clsf"),
    (
        "scikitgpc",
        "GaussianProcessClassifier",
        GaussianProcessClassifier,
        applicable_features,
        "clsf",
    ),
    (
        "scikitdtc",
        "DecisionTreeClassifier",
        DecisionTreeClassifier,
        applicable_features,
        "clsf",
    ),
    (
        "scikitrfc",
        "RandomForestClassifier",
        RandomForestClassifier,
        applicable_features,
        "clsf",
    ),
    ("scikitmlp", "MLPClassifier", MLPClassifier, applicable_features, "clsf"),
    ("scikitgnb", "GaussianNB", GaussianNB, applicable_features, "clsf"),
    (
        "scikitqda",
        "QuadraticDiscriminantAnalysis",
        QuadraticDiscriminantAnalysis,
        applicable_features,
        "clsf",
    ),
    (
        "scikitlr",
        "LinearRegression",
        LinearRegression,
        applicable_features,
        "reg",
    ),
    (
        "scikitlor",
        "LogisticRegression",
        LogisticRegression,
        applicable_features,
        "reg",
    ),
    (
        "scikitgbc",
        "GradientBoostingClassifier",
        GradientBoostingClassifier,
        applicable_features,
        "clsf",
    ),
    (
        "scikitetc",
        "ExtraTreesClassifier",
        ExtraTreesClassifier,
        applicable_features,
        "clsf",
    ),
    (
        "scikitbgc",
        "BaggingClassifier",
        BaggingClassifier,
        applicable_features,
        "clsf",
    ),
    ("scikiteln", "ElasticNet", ElasticNet, applicable_features, "clsf"),
    ("scikitbyr", "BayesianRidge", BayesianRidge, applicable_features, "reg"),
    ("scikitlas", "Lasso", Lasso, applicable_features, "reg"),
    ("scikitard", "ARDRegression", ARDRegression, applicable_features, "reg"),
    (
        "scikitrsc",
        "RANSACRegressor",
        RANSACRegressor,
        applicable_features,
        "reg",
    ),
    ("scikitbnb", "BernoulliNB", BernoulliNB, applicable_features, "clsf"),
    ("scikitmnb", "MultinomialNB", MultinomialNB, applicable_features, "clsf"),
    (
        "scikitlda",
        "LinearDiscriminantAnalysis",
        LinearDiscriminantAnalysis,
        applicable_features,
        "clsf",
    ),
    (
        "scikitdtr",
        "DecisionTreeRegressor",
        DecisionTreeRegressor,
        applicable_features,
        "reg",
    ),
    (
        "scikitgpr",
        "GaussianProcessRegressor",
        GaussianProcessRegressor,
        applicable_features,
        "reg",
    ),
    (
        "scikitomp",
        "OrthogonalMatchingPursuit",
        OrthogonalMatchingPursuit,
        applicable_features,
        "clsf",
    ),
    ("scikitridge", "Ridge", Ridge, applicable_features, "reg"),
    ("scikitlars", "Lars", Lars, applicable_features, "reg"),
    ("scikitkmeans", "KMeans", KMeans, applicable_features, "clstr"),
]:
    predict_field = (
        {"predict": (str, field("Label or the value to be predicted"))}
        if algo_type not in ["clstr"]
        else {}
    )
    dffml_config = mkscikit_config_cls(
        name + "ModelConfig",
        cls,
        properties={
            **{
                "directory": (
                    str,
                    field(
                        "Directory where state should be saved",
                        default=os.path.join(
                            os.path.expanduser("~"),
                            ".cache",
                            "dffml",
                            f"scikit-{entry_point_name}",
                        ),
                    ),
                ),
                "features": (Features, field("Features to train on")),
            },
            **predict_field,
        },
    )

    parentContext = (
        ScikitContext
        if algo_type not in ["clstr"]
        else ScikitContextUnsprvised
    )
    dffml_cls_ctx = type(
        name + "ModelContext",
        (parentContext,),
        {"applicable_features": applicable_features_function},
    )

    parentModel = Scikit if algo_type not in ["clstr"] else ScikitUnsprvised
    dffml_cls = type(
        name + "Model",
        (parentModel,),
        {
            "CONFIG": dffml_config,
            "CONTEXT": dffml_cls_ctx,
            "SCIKIT_MODEL": cls,
        },
    )
    # Add the ENTRY_POINT_ORIG_LABEL
    dffml_cls = entry_point(entry_point_name)(dffml_cls)

    setattr(sys.modules[__name__], dffml_config.__qualname__, dffml_config)
    setattr(sys.modules[__name__], dffml_cls_ctx.__qualname__, dffml_cls_ctx)
    setattr(sys.modules[__name__], dffml_cls.__qualname__, dffml_cls)
