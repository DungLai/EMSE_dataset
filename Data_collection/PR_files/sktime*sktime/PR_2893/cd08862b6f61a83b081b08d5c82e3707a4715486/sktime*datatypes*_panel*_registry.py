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
        "WARNING: only for internal use, not a fully supported Panel mtype. "
        "2D np.array of format (n_instances, n_columns*n_timepoints)",
    ),
    ("pd-multiindex", "Panel", "pd.DataFrame with multi-index (instances, timepoints)"),
    ("pd-wide", "Panel", "pd.DataFrame in wide format, cols = (instance*timepoints)"),
    (
        "pd-long",
        "Panel",
        "pd.DataFrame in long format, cols = (index, time_index, column)",
    ),
    ("df-list", "Panel", "list of pd.DataFrame"),
    (
        "listdataset",
        "Panel",
        "ATTENTION: Gluonts-only. List of dictionaries"
        "Each row is one instance. Can be univ or multiv. Fixed Freq.",
    ),
]

MTYPE_LIST_PANEL = pd.DataFrame(MTYPE_REGISTER_PANEL)[0].values
