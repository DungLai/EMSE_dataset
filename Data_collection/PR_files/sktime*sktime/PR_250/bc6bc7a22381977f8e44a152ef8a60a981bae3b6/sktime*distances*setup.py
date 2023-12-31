#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = "Markus LÃ¶ning"

import numpy
from numpy.distutils.misc_util import Configuration


def configuration(parent_package="", top_path=None):
    config = Configuration("distances", parent_package, top_path)

    config.add_extension(
        name="elastic_cython",
        sources=["elastic_cython.pyx"],
        include_dirs=[numpy.get_include()]
    )
    return config


if __name__ == "__main__":
    from numpy.distutils.core import setup

    setup(**configuration().todict())
