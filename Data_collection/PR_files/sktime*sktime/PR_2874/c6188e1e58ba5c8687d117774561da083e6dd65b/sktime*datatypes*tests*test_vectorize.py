# -*- coding: utf-8 -*-
"""Testing vectorization via VectorizedDF."""

__author__ = ["fkiraly"]

import numpy as np
import pandas as pd
import pytest

from sktime.datatypes import MTYPE_REGISTER, SCITYPE_REGISTER
from sktime.datatypes._check import AMBIGUOUS_MTYPES, check_is_mtype
from sktime.datatypes._examples import get_examples
from sktime.datatypes._vectorize import VectorizedDF, _enforce_index_freq
from sktime.utils._testing.deep_equals import deep_equals

SCITYPES = ["Panel", "Hierarchical"]


def _get_all_mtypes_for_scitype(scitype):
    """Return list of all mtypes for scitype.

    Parameters
    ----------
    scitype : str - scitype

    Returns
    -------
    mtypes : list of str - list of mtypes for scitype
    """
    if scitype not in [s[0] for s in SCITYPE_REGISTER]:
        raise RuntimeError(scitype + " is not in the SCITYPE_REGISTER")
    mtypes = [key[0] for key in MTYPE_REGISTER if key[1] == scitype]
    mtypes = [mtype for mtype in mtypes if mtype not in AMBIGUOUS_MTYPES]

    if len(mtypes) == 0:
        # if there are no mtypes, this must have been reached by mistake/bug
        raise RuntimeError("no mtypes defined for scitype " + scitype)

    return mtypes


def _generate_scitype_mtype_combinations():
    """Return scitype/mtype tuples for pytest_generate_tests.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    """
    # collect fixture tuples here

    sci_mtype_tuples = []

    for scitype in SCITYPES:

        mtypes = _get_all_mtypes_for_scitype(scitype)

        for mtype in mtypes:
            sci_mtype_tuples += [(scitype, mtype)]

    return sci_mtype_tuples


def _generate_scitype_mtype_fixtureindex_combinations():
    """Return fixture tuples for pytest_generate_tests.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    """
    # collect fixture tuples here

    sci_mtype_tuples = _generate_scitype_mtype_combinations()

    sci_mtype_index_tuples = []

    for tuple_j in sci_mtype_tuples:
        scitype = tuple_j[0]
        mtype = tuple_j[1]
        n_fixtures = len(get_examples(mtype=mtype, as_scitype=scitype))

        for i in range(n_fixtures):
            if get_examples(mtype=mtype, as_scitype=scitype).get(i) is not None:
                sci_mtype_index_tuples += [(scitype, mtype, i)]

    return sci_mtype_index_tuples


def pytest_generate_tests(metafunc):
    """Test parameterization routine for pytest.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    iterate_as : str - level on which to iterate over
    iterate_cols : bool - whether to iterate over columns
    """
    # we assume all four arguments are present in the test below

    fixturenames = set(metafunc.fixturenames)

    if set(["scitype", "mtype", "fixture_index"]).issubset(fixturenames):
        keys = _generate_scitype_mtype_fixtureindex_combinations()

        ids = []
        for tuple in keys:
            ids += [f"{tuple[0]}-{tuple[1]}-fixture:{tuple[2]}"]

        # parameterize test with from-mtpes
        metafunc.parametrize("scitype,mtype,fixture_index", keys, ids=ids)

    elif set(["scitype", "mtype"]).issubset(fixturenames):
        keys = _generate_scitype_mtype_combinations()

        ids = []
        for tuple in keys:
            ids += [f"{tuple[0]}-{tuple[1]}"]

        # parameterize test with from-mtpes
        metafunc.parametrize("scitype,mtype", keys, ids=ids)

    if "iterate_as" in fixturenames:
        metafunc.parametrize("iterate_as", ["Panel", "Series"])

    if "iterate_cols" in fixturenames:
        metafunc.parametrize("iterate_cols", [False, True])


def test_construct_vectorizeddf(scitype, mtype, fixture_index, iterate_cols):
    """Test that VectorizedDF constructs with valid arguments.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    iterate_cols : bool - whether to iterate over columns
    """
    # retrieve fixture for checking
    fixture = get_examples(mtype=mtype, as_scitype=scitype).get(fixture_index)

    # iterate as Series, without automated identification of scitype
    VectorizedDF(
        X=fixture, iterate_as="Series", is_scitype=scitype, iterate_cols=iterate_cols
    )

    # iterate as Series, with automated identification of scitype
    VectorizedDF(
        X=fixture, iterate_as="Series", is_scitype=None, iterate_cols=iterate_cols
    )

    # iterate as Panel, with automated identification of scitype
    VectorizedDF(
        X=fixture, iterate_as="Panel", is_scitype=None, iterate_cols=iterate_cols
    )


def test_construct_vectorizeddf_errors(scitype, mtype, fixture_index):
    """Test VectorizedDF raises appropriate errors with invalid arguments.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    """
    # retrieve fixture for checking
    fixture = get_examples(mtype=mtype, as_scitype=scitype).get(fixture_index)

    # if both iterate_as and as_scitype are "Panel", should raise an error
    with pytest.raises(ValueError, match=r'is_scitype is "Panel"'):
        VectorizedDF(X=fixture, iterate_as="Hierarchical", is_scitype="Panel")

    # invalid argument to iterate_as
    with pytest.raises(ValueError, match=r"iterate_as must be"):
        VectorizedDF(X=fixture, iterate_as="Pumuckl", is_scitype="Panel")

    # invalid argument to is_scitype
    with pytest.raises(ValueError, match=r"is_scitype must be"):
        VectorizedDF(X=fixture, iterate_as="Panel", is_scitype="Pumuckl")
    # we may have to change this if we introduce a "Pumuckl" scitype, but seems unlikely


def test_item_len(scitype, mtype, fixture_index, iterate_as, iterate_cols):
    """Tests __len__ returns correct length.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    iterate_as : str - level on which to iterate over
    iterate_cols : bool - whether to iterate over columns
    """
    # escape for the invalid Panel/Panel combination, see above

    # retrieve fixture for checking
    fixture = get_examples(mtype=mtype, as_scitype=scitype).get(fixture_index)

    # get true length
    if iterate_as == "Panel" and scitype == "Panel":
        true_length = 1
    elif iterate_as == "Series":
        _, _, metadata = check_is_mtype(
            fixture, mtype=mtype, scitype=scitype, return_metadata=True
        )
        true_length = metadata["n_instances"]
    elif iterate_as == "Panel":
        _, _, metadata = check_is_mtype(
            fixture, mtype=mtype, scitype=scitype, return_metadata=True
        )
        true_length = metadata["n_panels"]

    # construct VectorizedDF - we've tested above that this works
    X_vect = VectorizedDF(
        X=fixture, iterate_as=iterate_as, is_scitype=None, iterate_cols=iterate_cols
    )

    # if columns are being iterated over, length is multiplied by no columns iterated
    if iterate_cols:
        true_length = true_length * len(X_vect.X_multiindex.columns)

    # check length against n_instances metadata field
    assert len(X_vect) == true_length, (
        "X_vect.__len__ returns incorrect length.",
        f"True={true_length}, returned={len(X_vect)}",
    )


def test_iteration(scitype, mtype, fixture_index, iterate_as, iterate_cols):
    """Tests __getitem__ returns pd-multiindex mtype if iterate_as="Series".

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    iterate_as : str - level on which to iterate over
    iterate_cols : bool - whether to iterate over columns
    """
    # escape for the invalid Panel/Panel combination, see above
    if iterate_as == "Panel" and scitype == "Panel":
        return None

    # retrieve fixture for checking
    fixture = get_examples(mtype=mtype, as_scitype=scitype).get(fixture_index)

    # construct VectorizedDF - we've tested above that this works
    X_vect = VectorizedDF(
        X=fixture, iterate_as=iterate_as, is_scitype=None, iterate_cols=iterate_cols
    )

    # testing list comprehension works with indexing
    X_iter1 = [X_vect[i] for i in range(len(X_vect))]
    assert isinstance(X_iter1, list)

    # testing that iterator comprehension works
    X_iter2 = [X_idx for X_idx in X_vect]
    assert isinstance(X_iter2, list)

    # testing that as_list method works
    X_iter3 = X_vect.as_list()
    assert isinstance(X_iter3, list)

    # check that these are all the same
    assert deep_equals(X_iter1, X_iter2)
    assert deep_equals(X_iter2, X_iter3)


def test_series_item_mtype(scitype, mtype, fixture_index, iterate_as, iterate_cols):
    """Tests __getitem__ returns correct pd-multiindex mtype.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    iterate_as : str - level on which to iterate over
    iterate_cols : bool - whether to iterate over columns
    """
    # escape for the invalid Panel/Panel combination, see above
    if iterate_as == "Panel" and scitype == "Panel":
        return None

    # retrieve fixture for checking
    fixture = get_examples(mtype=mtype, as_scitype=scitype).get(fixture_index)

    # construct VectorizedDF - we've tested above that this works
    X_vect = VectorizedDF(
        X=fixture, iterate_as=iterate_as, is_scitype=None, iterate_cols=iterate_cols
    )

    # get list of iterated elements - we've tested above that this works
    X_list = list(X_vect)

    # right mtype depends on scitype
    if iterate_as == "Series":
        correct_mtype = "pd.DataFrame"
    elif iterate_as == "Panel":
        correct_mtype = "pd-multiindex"
    else:
        RuntimeError(f"found unexpected iterate_as value: {iterate_as}")

    X_list_valid = [
        check_is_mtype(X, mtype=correct_mtype, scitype=iterate_as) for X in X_list
    ]

    assert np.all(
        X_list_valid
    ), f"iteration elements do not conform with expected mtype {correct_mtype}"


def test_reconstruct_identical(scitype, mtype, fixture_index, iterate_as, iterate_cols):
    """Tests that reconstruct recreates the original input X.

    Fixtures parameterized
    ----------------------
    scitype : str - scitype of fixture
    mtype : str - mtype of fixture
    fixture_index : int - index of fixture tuple with that scitype and mtype
    iterate_as : str - level on which to iterate over
    iterate_cols : bool - whether to iterate over columns

    Raises
    ------
    RuntimeError if scitype is not defined or has no mtypes or examples
    AssertionError if examples are not correctly identified
    error if check itself raises an error
    """
    # escape for the invalid Panel/Panel combination, see above
    if iterate_as == "Panel" and scitype == "Panel":
        return None

    # retrieve fixture for checking
    fixture = get_examples(mtype=mtype, as_scitype=scitype).get(fixture_index)

    # construct VectorizedDF - we've tested above that this works
    X_vect = VectorizedDF(
        X=fixture, iterate_as=iterate_as, is_scitype=None, iterate_cols=iterate_cols
    )

    # get list of iterated elements - we've tested above that this yields correct result
    X_list = list(X_vect)

    # reconstructed fixture should equal multiindex fixture if not convert_back
    assert deep_equals(X_vect.reconstruct(X_list), X_vect.X_multiindex)

    # reconstructed fixture should equal original fixture if convert_back
    assert deep_equals(X_vect.reconstruct(X_list, convert_back=True), fixture)


@pytest.mark.parametrize(
    "item, freq",
    [
        (
            pd.Series(
                data=1,
                index=pd.DatetimeIndex(
                    ["2000-01-01", "2000-01-02", "2000-01-03", "2000-01-04"], freq="D"
                ),
            ),
            "D",
        ),
        (
            pd.Series(
                data=1,
                index=pd.DatetimeIndex(
                    ["2000-01-01", "2000-01-02", "2000-01-03", "2000-01-04"], freq=None
                ),
            ),
            "D",
        ),
        (
            pd.Series(
                data=1,
                index=pd.DatetimeIndex(
                    ["2000-01-01", "2000-01-03", "2000-01-03", "2000-01-09"], freq=None
                ),
            ),
            None,
        ),
    ],
)
def test_enforce_index_freq(item, freq):
    """Tests that enforce freq infers the right frequency."""
    item = _enforce_index_freq(item)
    assert item.index.freq == freq
