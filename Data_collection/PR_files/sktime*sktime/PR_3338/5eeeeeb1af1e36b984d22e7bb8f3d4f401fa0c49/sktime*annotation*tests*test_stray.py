# -*- coding: utf-8 -*-
"""Tests for STRAY outlier estimator."""

__author__ = ["KatieBuc"]

import numpy as np


def test_one_dimensional():

    X = np.array(
        [
            -7.207066,
            -5.722571,
            -4.915559,
            -8.345698,
            -5.570875,
            -5.493944,
            -6.574740,
            -6.546632,
            -6.564452,
            -6.890038,
            -6.477193,
            -6.998386,
            -6.776254,
            -5.935541,
            -5.040506,
            0.000000,
            5.889715,
            5.488990,
            5.088805,
            5.162828,
            8.415835,
            6.134088,
            5.509314,
            5.559452,
            6.459589,
            5.306280,
            4.551795,
            6.574756,
            4.976344,
            5.984862,
            5.064051,
            7.102298,
        ]
    )

    y_pred_expected = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
    ]

    assert np.allclose(y_pred_actual, y_pred_expected)


def test_high_dimensional():

    X = np.array(
        [
            [-1.207, -0.776, -0.694],
            [0.277, 0.064, -1.448],
            [1.084, 0.959, 0.575],
            [-2.346, -0.110, -1.024],
            [0.429, -0.511, -0.015],
            [0.506, -0.911, -0.936],
            [-0.575, -0.837, 1.102],
            [-0.547, 2.416, -0.476],
            [-0.564, 0.134, -0.709],
            [-0.890, -0.491, -0.501],
            [-0.477, -0.441, -1.629],
            [-0.998, 0.460, -1.168],
            [
                10.000,
                12.000,
                10.000,
            ],
            [
                3.000,
                7.000,
                10.000,
            ],
        ]
    )

    y_pred_expected = [
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        0,
        1,
        1,
    ]

    assert np.allclose(y_pred_actual, y_pred_expected)
