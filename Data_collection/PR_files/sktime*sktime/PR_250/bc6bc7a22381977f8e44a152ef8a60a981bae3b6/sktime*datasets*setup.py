#!/usr/bin/env python3 -u
# coding: utf-8

__author__ = "Markus LÃ¶ning"


# adapted from https://github.com/scikit-learn/scikit-learn/blob/master
# /sklearn/datasets/setup.py


def configuration(parent_package='', top_path=None):
    from numpy.distutils.misc_util import Configuration
    config = Configuration('datasets', parent_package, top_path)

    # add all datasets in sub-folders
    included_datasets = (
        "ArrowHead",
        "BasicMotions",
        "GunPoint",
        "ItalyPowerDemand",
        "JapaneseVowels",
        "Longley",
        "Lynx",
        "PLAID",
        "ShampooSales",
        "Airline"
    )
    for dataset in included_datasets:
        config.add_data_dir(f"data/{dataset}")

    return config


if __name__ == '__main__':
    from numpy.distutils.core import setup

    setup(**configuration(top_path='').todict())
