import os
import sys
import site
import importlib.util
from setuptools import setup

# See https://github.com/pypa/pip/issues/7953
site.ENABLE_USER_SITE = "--user" in sys.argv[1:]

# Boilerplate to load commonalities
spec = importlib.util.spec_from_file_location(
    "setup_common", os.path.join(os.path.dirname(__file__), "setup_common.py")
)
common = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common)

common.KWARGS["entry_points"] = {
    "dffml.model": [
        f"xgbregressor = {common.IMPORT_NAME}.xgbregressor:XGBRegressorModel",
        f"xgbclassifier = {common.IMPORT_NAME}.xgbclassifier:XGBClassifierModel",
    ]
}

setup(**common.KWARGS)