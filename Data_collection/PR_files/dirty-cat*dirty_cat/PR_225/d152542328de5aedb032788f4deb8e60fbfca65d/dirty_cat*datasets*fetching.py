# -*- coding: utf-8 -*-

"""
Fetching functions to retrieve example datasets, using
Scikit-Learn's ``fetch_openml()`` function.
"""


# Author:
# Lilian Boulard <lilian@boulard.fr>
# https://github.com/LilianBoulard

# Future notes:
# - Watch out for ``fetch_openml()`` API modifications:
# as of january 2021, the function is marked as experimental.


import gzip
import json
import sklearn
import warnings
import pandas as pd

from pathlib import Path
from dataclasses import dataclass
from typing import Union, Dict, Any, List
from distutils.version import LooseVersion

from dirty_cat.datasets.utils import get_data_dir


# Directory where the ``.gz`` files containing the
# details on downloaded datasets are stored.
# Note: the tree structure is created by ``fetch_openml()``.
# As of october 2020, this function is annotated as
# ``Experimental`` so the structure might change in future releases.
# This path will be concatenated to the dirty_cat data directory,
# available via the function ``get_data_dir()``.
DETAILS_DIRECTORY = "openml/openml.org/api/v1/json/data/"

# Same as above ; for the datasets features location.
FEATURES_DIRECTORY = "openml/openml.org/api/v1/json/data/features/"

# Same as above ; for the datasets data location.
DATA_DIRECTORY = "openml/openml.org/data/v1/download/"

# The IDs of the datasets, from OpenML.
# For each dataset, its URL is constructed as follows:
openml_url = "https://www.openml.org/d/{ID}"
ROAD_SAFETY_ID = 42803
OPEN_PAYMENTS_ID = 42738
MIDWEST_SURVEY_ID = 42805
MEDICAL_CHARGE_ID = 42720
EMPLOYEE_SALARIES_ID = 42125
TRAFFIC_VIOLATIONS_ID = 42132
DRUG_DIRECTORY_ID = 43044


@dataclass
class Details:
    name: str
    file_id: int
    description: str


@dataclass
class Features:
    names: List[str]


@dataclass
class DatasetAll:
    """Dataclass representing a dataset (loaded in memory).

    Attributes
    ----------

    description
        Description explaining the content of the dataset

    X
        Dataset as a pandas DataFrame. Does not contain `y`

    y
        Target column, usually referred to as `y`

    source
        The dataset's URL on OpenML

    path
        Local path of the CSV file containing the dataset

    """

    description: str
    X: pd.DataFrame
    y: pd.Series
    source: str
    path: Path


@dataclass
class DatasetInfoOnly:

    """Dataclass representing a dataset (not loaded in memory).

    Attributes
    ----------

    description
        Description explaining the content of the dataset

    source
        The dataset's URL on OpenML

    path
        Local path of the CSV file containing the dataset

    read_csv_kwargs
        Keyword arguments that can be passed to `read_csv`
        (when loading dataset from `path`).
        Usage:
        ```
        >>> data: DatasetInfoOnly
        >>> df = pd.read_csv(data.path, **data.read_csv_kwargs)
        ```

    """

    description: str
    source: str
    path: Path
    read_csv_kwargs: Dict[str, Any]


def fetch_openml_dataset(dataset_id: int,
                         data_directory: Path = get_data_dir()) -> dict:
    """
    Gets a dataset from OpenML (https://www.openml.org),
    or from the disk if already downloaded.

    Parameters
    ----------
    dataset_id: int
        The ID of the dataset to fetch.
    data_directory: Path
        Optional. A directory to save the data to.
        By default, the dirty_cat data directory.

    Returns
    -------
    dict
        A dictionary containing:
          - ``description``: str
              The description of the dataset,
              as gathered from OpenML.
          - ``source``: str
              The dataset's URL from OpenML.
          - ``path``: pathlib.Path
              The local path leading to the dataset,
              saved as a CSV file.

          The following values are added by the fetches below (fetch_*)
          - ``read_csv_kwargs``: Dict[str, Any]
              A dict of keyword arguments that can be passed to
              `pandas.read_csv` for reading.
              Usually, it contains `quotechar`, `escapechar` and `na_values`.
              Use by passing `**info['read_csv_kwargs']` to `read_csv`.
              e.g., `df = pd.read_csv(info['path'], **info['read_csv_kwargs'])`
          - ``target``: str
              The name of `y`, the target column.

    """
    # Make path absolute
    data_directory = data_directory.resolve()

    # Construct the path to the gzip file containing the details on a dataset.
    details_gz_path = data_directory / DETAILS_DIRECTORY / f'{dataset_id}.gz'
    features_gz_path = data_directory / FEATURES_DIRECTORY / f'{dataset_id}.gz'

    if not details_gz_path.is_file() or not features_gz_path.is_file():
        # If the details file or the features file don't exist,
        # download the dataset.
        warnings.warn(
            f"Could not find the dataset {dataset_id} locally. "
            "Downloading it from OpenML; this might take a while... "
            "If it is interrupted, some files might be invalid/incomplete: "
            "if on the following run, the fetching raises errors, you can try "
            f"fixing this issue by deleting the directory {data_directory!r}."
        )
        _download_and_write_openml_dataset(dataset_id=dataset_id,
                                           data_directory=data_directory)
    details = _get_details(details_gz_path)

    # The file ID is required because the data file is named after this ID,
    # and not after the dataset's.
    file_id = details.file_id
    csv_path = data_directory / f'{details.name}.csv'

    data_gz_path = data_directory / DATA_DIRECTORY / f'{file_id}.gz'

    if not data_gz_path.is_file():
        # This is a double-check.
        # If the data file does not exist, download the dataset.
        _download_and_write_openml_dataset(dataset_id=dataset_id,
                                           data_directory=data_directory)

    if not csv_path.is_file():
        # If the CSV file does not exist, use the dataset
        # downloaded by ``fetch_openml()`` to construct it.
        features = _get_features(features_gz_path)
        _export_gz_data_to_csv(data_gz_path, csv_path, features)

    url = openml_url.format(ID=dataset_id)

    return {
        "description": details.description,
        "source": url,
        "path": csv_path.resolve()
    }


def _download_and_write_openml_dataset(dataset_id: int,
                                       data_directory: Path) -> None:
    """
    Downloads a dataset from OpenML,
    taking care of creating the directories.

    Parameters
    ----------
    dataset_id: int
        The ID of the dataset to download.
    data_directory: Path
        The directory in which the data will be saved.

    Raises
    ------
    ValueError
        If the ID is incorrect (does not exist on OpenML)
    urllib.error.URLError
        If there is no Internet connection.

    """
    from sklearn.datasets import fetch_openml

    fetch_kwargs = {}
    if LooseVersion(sklearn.__version__) >= LooseVersion('0.22'):
        fetch_kwargs.update({'as_frame': True})

    # The ``fetch_openml()`` function returns a Scikit-Learn ``Bunch`` object,
    # which behaves just like a ``namedtuple``.
    # However, we do not want to save this data into memory:
    # we will read it from the disk later.
    #
    # Raises ``ValueError`` if the ID is incorrect (does not exist on OpenML)
    # and ``urllib.error.URLError`` if there is no Internet connection.
    fetch_openml(
        data_id=dataset_id,
        data_home=str(data_directory),
        **fetch_kwargs
    )


def _read_json_from_gz(compressed_dir_path: Path) -> dict:
    """
    Opens a gzip file, reads its content (JSON expected),
    and returns a dictionary.

    Parameters
    ----------
    compressed_dir_path: Path
        Path to the ``.gz`` file to read.

    Returns
    -------
    dict
        The information contained in the file,
        converted from plain-text JSON.

    """
    if not compressed_dir_path.is_file():
        raise FileNotFoundError(f"Couldn't find file {compressed_dir_path!s}")

    # Read content
    with gzip.open(compressed_dir_path, mode='rt') as gz:
        content = gz.read()

    details_json = json.JSONDecoder().decode(content)
    return details_json


def _get_details(compressed_dir_path: Path) -> Details:
    """
    Gets useful details from the details file.

    Parameters
    ----------
    compressed_dir_path: Path
        The path to the ``.gz`` file containing the details.

    Returns
    -------
    Details
        A ``Details`` object.

    """
    details = _read_json_from_gz(compressed_dir_path)["data_set_description"]
    # We filter out the irrelevant information.
    # If you want to modify this list (to add or remove items)
    # you must also modify the ``Details`` object definition.
    f_details = {
        "name": details["name"],
        "file_id": details["file_id"],
        "description": details["description"],
    }
    return Details(*f_details.values())


def _get_features(compressed_dir_path: Path) -> Features:
    """
    Gets features that can be inserted in the CSV file.
    The most important feature being the column names.

    Parameters
    ----------
    compressed_dir_path: Path
        Path to the gzip file containing the features.

    Returns
    -------
    Features
        A ``Features`` object.

    """
    raw_features = _read_json_from_gz(compressed_dir_path)["data_features"]
    # We filter out the irrelevant information.
    # If you want to modify this list (to add or remove items)
    # you must also modify the ``Features`` object definition.
    features = {
        "names": [column["name"] for column in raw_features["feature"]]
    }
    return Features(*features.values())


def _export_gz_data_to_csv(compressed_dir_path: Path,
                           destination_file: Path, features: Features) -> None:
    """
    Reads a gzip file containing ARFF data,
    and writes it to a target CSV.

    Parameters
    ----------
    compressed_dir_path: Path
        Path to the ``.gz`` file containing the ARFF data.
    destination_file: Path
        A CSV file to write to.
    features: Features
        A ``Features`` object containing the first CSV line (the column names).

    """
    atdata_found = False
    with destination_file.open(mode="w", encoding='utf8') as csv:
        with gzip.open(compressed_dir_path, mode="rt", encoding='utf8') as gz:
            csv.write(_features_to_csv_format(features))
            csv.write("\n")
            # We will look at each line of the file until we find
            # "@data": only after this tag is the actual CSV data.
            for line in gz.readlines():
                if not atdata_found:
                    if line.lower().startswith("@data"):
                        atdata_found = True
                else:
                    csv.write(line)


def _features_to_csv_format(features: Features) -> str:
    return ",".join(features.names)


def fetch_dataset_as_namedtuple(dataset_id: int, target: str,
                               read_csv_kwargs: dict,
                               load_dataframe: bool,
                               ) -> Union[DatasetAll, DatasetInfoOnly]:
    warnings.warn('Method `fetch_dataset_as_namedtuple` is deprecated, '
                  'use `fetch_dataset_as_dataclass` instead')
    return fetch_dataset_as_dataclass(dataset_id, target,
                                      read_csv_kwargs, load_dataframe)


def fetch_dataset_as_dataclass(dataset_id: int, target: str,
                               read_csv_kwargs: dict,
                               load_dataframe: bool,
                               ) -> Union[DatasetAll, DatasetInfoOnly]:
    """
    Takes a dataset identifier, a target column name,
    and some additional keyword arguments for `pd.read_csv`.

    If you don't need the dataset to be loaded in memory,
    pass `load_dataframe=False`.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    """
    info = fetch_openml_dataset(dataset_id)
    if load_dataframe:
        df = pd.read_csv(info['path'], **read_csv_kwargs)
        y = df[target]
        X = df.drop(target, axis='columns')
        dataset = DatasetAll(
            description=info['description'],
            X=X,
            y=y,
            source=info['source'],
            path=info['path'],
        )
    else:
        dataset = DatasetInfoOnly(
            description=info['description'],
            source=info['source'],
            path=info['path'],
            read_csv_kwargs=read_csv_kwargs,
        )

    return dataset


# Datasets fetchers section
# Public API


def fetch_employee_salaries(load_dataframe: bool = True,
                            drop_linked: bool = True,
                            drop_irrelevant: bool = True,
                            ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the employee_salaries dataset.

    Parameters
    ----------
    drop_linked: bool (default True)
        Drops columns "2016_gross_pay_received" and "2016_overtime_pay",
        which are closely linked to "current_annual_salary", the target.

    drop_irrelevant: bool (default True)
        Drops column "full_name", which is usually irrelevant to the
        statistical analysis.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    dataset = fetch_dataset_as_dataclass(
        dataset_id=EMPLOYEE_SALARIES_ID,
        target='current_annual_salary',
        read_csv_kwargs={
            'quotechar': "'",
            'escapechar': '\\',
            'na_values': ['?'],
        },
        load_dataframe=load_dataframe,
    )
    if load_dataframe:
        if drop_linked:
            dataset.X.drop(["2016_gross_pay_received", "2016_overtime_pay"],
                           axis=1, inplace=True)
        if drop_irrelevant:
            dataset.X.drop(["full_name"], axis=1, inplace=True)

    return dataset


def fetch_road_safety(load_dataframe: bool = True,
                      ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the road safety dataset.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    return fetch_dataset_as_dataclass(
        dataset_id=ROAD_SAFETY_ID,
        target='Sex_of_Driver',
        read_csv_kwargs={
            'na_values': ['?'],
        },
        load_dataframe=load_dataframe,
    )


def fetch_medical_charge(load_dataframe: bool = True
                         ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the medical charge dataset.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    return fetch_dataset_as_dataclass(
        dataset_id=MEDICAL_CHARGE_ID,
        target='Average_Total_Payments',
        read_csv_kwargs={
            'quotechar': "'",
            'escapechar': '\\',
        },
        load_dataframe=load_dataframe,
    )


def fetch_midwest_survey(load_dataframe: bool = True
                         ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the midwest survey dataset.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    return fetch_dataset_as_dataclass(
        dataset_id=MIDWEST_SURVEY_ID,
        target='Census_Region',
        read_csv_kwargs={
            'quotechar': "'",
            'escapechar': '\\',
        },
        load_dataframe=load_dataframe,
    )


def fetch_open_payments(load_dataframe: bool = True
                        ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the open payments dataset.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    return fetch_dataset_as_dataclass(
        dataset_id=OPEN_PAYMENTS_ID,
        target='status',
        read_csv_kwargs={
            'quotechar': "'",
            'escapechar': '\\',
            'na_values': ['?'],
        },
        load_dataframe=load_dataframe,
    )


def fetch_traffic_violations(load_dataframe: bool = True
                             ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the traffic violations dataset.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    return fetch_dataset_as_dataclass(
        dataset_id=TRAFFIC_VIOLATIONS_ID,
        target='violation_type',
        read_csv_kwargs={
            'quotechar': "'",
            'escapechar': '\\',
            'na_values': ['?'],
        },
        load_dataframe=load_dataframe,
    )


def fetch_drug_directory(load_dataframe: bool = True
                         ) -> Union[DatasetAll, DatasetInfoOnly]:
    """Fetches the drug directory dataset.

    Returns
    -------
    DatasetAll
        If `load_dataframe=True`

    DatasetInfoOnly
        If `load_dataframe=False`

    See Also
    --------
    dirty_cat.datasets.fetch_dataset_as_namedtuple : additional information
    """
    return fetch_dataset_as_dataclass(
        dataset_id=DRUG_DIRECTORY_ID,
        target='PRODUCTTYPENAME',
        read_csv_kwargs={
            'quotechar': "'",
            'escapechar': '\\',
        },
        load_dataframe=load_dataframe,
    )
