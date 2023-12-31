# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# http://www.sphinx-doc.org/en/master/config

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys

sys.path.insert(0, os.path.abspath("."))
from dffml.version import VERSION

# -- Project information -----------------------------------------------------

project = "DFFML"
copyright = "2019, Intel"
author = "John Andersen"

# The short X.Y version
version = VERSION

# The full version, including alpha/beta/rc tags
release = version


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.viewcode",
    "sphinx.ext.napoleon",
    "sphinx.ext.doctest",
    "sphinxcontrib.asyncio",
    "recommonmark",
]

intersphinx_mapping = {"python": ("https://docs.python.org/3", None)}

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []

# Enable markdown
source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

html_theme_options = {
    "description": "The fastest path to machine learning integration",
    "github_user": "intel",
    "github_repo": "dffml",
    "github_button": True,
    "travis_button": True,
    "codecov_button": True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

# -- Extension configuration -------------------------------------------------

napoleon_numpy_docstring = True

doctest_global_setup = """
import os
import sys
import shutil
import atexit
import inspect
import asyncio
import tempfile
import functools

# Create a temporary directory for test to run in
DOCTEST_TEMPDIR = tempfile.mkdtemp()
# Remove it when the test exits
atexit.register(functools.partial(shutil.rmtree, DOCTEST_TEMPDIR))
# Change the current working directory to the temporary directory
os.chdir(DOCTEST_TEMPDIR)

from dffml.base import *
from dffml.df.base import *
from dffml.util.net import *
"""
