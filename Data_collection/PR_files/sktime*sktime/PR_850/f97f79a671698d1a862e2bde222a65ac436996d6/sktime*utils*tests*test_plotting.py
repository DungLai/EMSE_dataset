# -*- coding: utf-8 -*-
import numpy as np
import pandas as pd
import pytest

from sktime.datasets import load_airline
from sktime.utils.plotting import plot_series, plot_correlations
from sktime.utils.validation._dependencies import _check_soft_dependencies
from sktime.utils.validation.series import VALID_DATA_TYPES

ALLOW_NUMPY = False
y_airline = load_airline()
y_airline_true = y_airline.iloc[y_airline.index < "1960-01"]
y_airline_test = y_airline.iloc[y_airline.index >= "1960-01"]
series_to_test = [y_airline, (y_airline_true, y_airline_test)]


def _plot_series(series, ax=None, **kwargs):
    if isinstance(series, tuple):
        return plot_series(*series, ax=ax, **kwargs)
    else:
        return plot_series(series, ax=ax, **kwargs)


@pytest.fixture
def valid_data_types():
    valid_data_types = tuple(filter(lambda x: x is not np.ndarray, VALID_DATA_TYPES))
    return valid_data_types


@pytest.mark.parametrize("series_to_plot", series_to_test)
def test_plot_series_runs_without_error(series_to_plot):
    _check_soft_dependencies("matplotlib", "seaborn")
    import matplotlib.pyplot as plt

    _plot_series(series_to_plot)
    plt.gcf().canvas.draw_idle()


@pytest.mark.parametrize("series_to_plot", [y_airline.values, "this_is_a_string"])
def test_plot_series_invalid_input_type_raises_error(series_to_plot, valid_data_types):
    # TODO: Is it possible to dynamically create the matching str if it includes
    #       characters that need to be escaped (like .)
    # match = f"Data must be a one of {valid_data_types}, but found type: {type(Z)}"
    with pytest.raises(TypeError):
        _plot_series(series_to_plot)


@pytest.mark.parametrize(
    "series_to_plot", [(y_airline_true, y_airline_test.reset_index(drop=True))]
)
def test_plot_series_with_unequal_index_type_raises_error(
    series_to_plot, valid_data_types
):
    match = "Found series with different index types."
    with pytest.raises(TypeError, match=match):
        _plot_series(series_to_plot)


@pytest.mark.parametrize("series_to_plot", series_to_test)
def test_plot_series_invalid_marker_kwarg_len_raises_error(series_to_plot):
    match = """There must be one marker for each time series,
                but found inconsistent numbers of series and
                markers."""
    with pytest.raises(ValueError, match=match):
        # Generate error by creating list of markers with length that does
        # not match input number of input series
        if isinstance(series_to_plot, pd.Series):
            markers = ["o", "o"]
        elif isinstance(series_to_plot, pd.DataFrame):
            markers = ["o" for _ in range(series_to_plot.shape[1] - 1)]
        elif isinstance(series_to_plot, tuple):
            markers = ["o" for _ in range(len(series_to_plot) - 1)]

        _plot_series(series_to_plot, markers=markers)


@pytest.mark.parametrize("series_to_plot", series_to_test)
def test_plot_series_invalid_label_kwarg_len_raises_error(series_to_plot):
    match = """There must be one label for each time series,
                but found inconsistent numbers of series and
                labels."""
    with pytest.raises(ValueError, match=match):
        # Generate error by creating list of labels with length that does
        # not match input number of input series
        if isinstance(series_to_plot, pd.Series):
            labels = ["Series 1", "Series 2"]
        elif isinstance(series_to_plot, pd.DataFrame):
            labels = [f"Series {i}" for i in range(series_to_plot.shape[1] - 1)]
        elif isinstance(series_to_plot, tuple):
            labels = [f"Series {i}" for i in range(len(series_to_plot) - 1)]

        _plot_series(series_to_plot, labels=labels)


@pytest.mark.parametrize("series_to_plot", series_to_test)
def test_plot_series_output_type(series_to_plot):
    _check_soft_dependencies("matplotlib", "seaborn")
    import matplotlib.pyplot as plt

    # Test output case where kwarg ax=None
    fig, ax = _plot_series(series_to_plot)

    is_fig_figure = isinstance(fig, plt.Figure)
    is_ax_axis = isinstance(ax, plt.Axes)

    assert is_fig_figure and is_ax_axis, "".join(
        [
            "plot_series with kwarg ax=None should return plt.Figure and plt.Axes,",
            f"but returned: {type(fig)} and {type(ax)}",
        ]
    )

    # Test output case where an existing plt.Axes object is passed to kwarg ax
    fig, ax = plt.subplots(1, figsize=plt.figaspect(0.25))
    ax = _plot_series(series_to_plot, ax=ax)

    is_ax_axis = isinstance(ax, plt.Axes)

    assert is_ax_axis, "".join(
        [
            "plot_series with plt.Axes object passed to kwarg ax",
            f"should return plt.Axes, but returned: {type(ax)}",
        ]
    )


@pytest.mark.parametrize("series_to_plot", [y_airline])
def test_plot_correlations_runs_without_error(series_to_plot):
    _check_soft_dependencies("matplotlib")
    import matplotlib.pyplot as plt

    plot_correlations(series_to_plot)
    plt.gcf().canvas.draw_idle()


@pytest.mark.parametrize("series_to_plot", [y_airline.values, "this_is_a_string"])
def test_plot_correlations_invalid_input_type_raises_error(
    series_to_plot, valid_data_types
):
    # TODO: Is it possible to dynamically create the matching str if it includes
    #       characters that need to be escaped (like .)
    # match = f"Data must be a one of {valid_data_types}, but found type: {type(Z)}"
    with pytest.raises(TypeError):
        plot_correlations(series_to_plot)


@pytest.mark.parametrize("series_to_plot", [y_airline])
def test_plot_correlations_output_type(series_to_plot):
    _check_soft_dependencies("matplotlib")
    import matplotlib.pyplot as plt

    fig, ax = plot_correlations(series_to_plot)

    is_fig_figure = isinstance(fig, plt.Figure)
    is_ax_array = isinstance(ax, np.ndarray)
    is_ax_array_axis = all([isinstance(ax_, plt.Axes) for ax_ in ax])

    assert is_fig_figure and is_ax_array and is_ax_array_axis, "".join(
        [
            "plot_correlations should return plt.Figure and array of plt.Axes,",
            f"but returned: {type(fig)} and {type(ax)}",
        ]
    )