# Copyright (c) Microsoft Corporation and contributors.
# Licensed under the MIT License.

import os
import sys
from setuptools import setup, find_packages


MINIMUM_PYTHON_VERSION = 3, 6  # Minimum of Python 3.6

if sys.version_info < MINIMUM_PYTHON_VERSION:
    sys.exit("Python {}.{}+ is required.".format(*MINIMUM_PYTHON_VERSION))

sys.path.insert(0, os.path.join("graspy", "version"))
# TODO: #454 Change path in https://github.com/microsoft/graspologic/issues/454
from version import version
sys.path.pop(0)

version_path = os.path.join("graspy", "version", "version.txt")
with open(version_path, "w") as version_file:
    version_file.write(f"{version}")

with open("README.md", "r") as f:
    LONG_DESCRIPTION = f.read()

setup(
    name="graspy",
    version=version,
    description="A set of python modules for graph statistics",
    long_description=LONG_DESCRIPTION,
    long_description_content_type="text/markdown",
    author="Eric Bridgeford, Jaewon Chung, Benjamin Pedigo, Bijan Varjavand",
    author_email="j1c@jhu.edu",
    maintainer="Dwayne Pryce",
    maintainer_email="dwpryce@microsoft.com",
    url="https://github.com/microsoft/graspologic",
    license="MIT",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Mathematics",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    packages=find_packages(exclude=["tests", "tests.*", "tests/*"]),
    include_package_data=True,
    package_data={
        "version": [os.path.join("graspy", "version", "version.txt")]
    },  # TODO: #454 Also needs changed by https://github.com/microsoft/graspologic/issues/454
    install_requires=[
        "networkx>=2.1",
        "numpy>=1.8.1",
        "scikit-learn>=0.19.1",
        "scipy>=1.4.0",
        "seaborn>=0.9.0",
        "matplotlib>=3.0.0,<=3.3.0",
        "hyppo>=0.1.3",
    ],
    extras_require={
        "dev": [
            "black",
            "mypy",
            "pytest",
            "pytest-cov",
            "sphinx-rtd-theme"
        ]
    }
)
