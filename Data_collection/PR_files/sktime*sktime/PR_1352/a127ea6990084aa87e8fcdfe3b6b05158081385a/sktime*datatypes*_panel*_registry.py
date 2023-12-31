# -*- coding: utf-8 -*-

import pandas as pd

__all__ = [
    "MTYPE_REGISTER_PANEL",
    "MTYPE_LIST_PANEL",
]


MTYPE_REGISTER_PANEL = [
    (
        "nested_univ",
        "Panel",
        "pd.DataFrame with one column per variable, pd.Series in cells",
    ),
    (
        "numpy3D",
        "Panel",
        "3D np.array of format (n_instances, n_columns, n_timepoints)",
    ),
    (
        "numpyflat",
        "Panel",
        "2D np.array of format (n_instances, n_columns*n_timepoints)",
    ),
    ("pd-multiindex", "Panel", "pd.DataFrame with multi-index (instance, time point)"),
    ("pd-wide", "Panel", "pd.DataFrame in wide format, cols = (instance*time point)"),
    (
        "pd-long",
        "Panel",
        "pd.DataFrame in long format, cols = (index, time_index, column)",
    ),
    ("df-list", "Panel", "list of pd.DataFrame"),
]

MTYPE_LIST_PANEL = pd.DataFrame(MTYPE_REGISTER_PANEL)[0].values
