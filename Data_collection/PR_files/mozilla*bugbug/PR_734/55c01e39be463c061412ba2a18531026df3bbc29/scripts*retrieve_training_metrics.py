# -*- coding: utf-8 -*-

import argparse
import logging
import sys

import requests
import taskcluster

from bugbug.utils import get_taskcluster_options

ROOT_URI = "train_{}.per_date"
DATE_URI = "train_{}.per_date.{}"
PROJECT_PREFIX = "project.relman.bugbug.{}"
BASE_URL = "https://index.taskcluster.net/v1/task/{}/artifacts/public/metrics.json"
NAMESPACE_URI = "project.relman.bugbug.{}"

LOGGER = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


def get_task_metrics_from_uri(index_uri):
    index_url = BASE_URL.format(index_uri)
    LOGGER.info(f"Retrieving metrics from {index_url}")
    r = requests.get(index_url)

    if r.status_code == 404:
        LOGGER.error(f"File not found for URL {index_url}, check your arguments")
        sys.exit(1)

    r.raise_for_status()

    return r


def get_namespaces(index, index_uri):
    index_namespaces = index.listNamespaces(index_uri)

    return index_namespaces["namespaces"]


def is_later_or_equal(partial_date, from_date):
    for partial_date_part, from_date_part in zip(partial_date, from_date):
        if int(partial_date_part) > int(from_date_part):
            return True
        elif int(partial_date_part) < int(from_date_part):
            return False
        else:
            continue

    return True


def get_task_metrics_from_date(model, date):
    options = get_taskcluster_options()

    index = taskcluster.Index(options)

    index.ping()

    # Split the date
    from_date = date.split(".")

    uris = []
    uris.append([])

    # Recursively list all namespaces greater or equals than the given date
    while uris:
        uri = uris.pop(0)

        # Handle version level namespaces
        if not uri:
            index_uri = ROOT_URI.format(model)
        else:
            uri_date = ".".join(uri)
            index_uri = DATE_URI.format(model, uri_date)

        index_uri = NAMESPACE_URI.format(index_uri)

        tasks = index.listTasks(index_uri)
        for task in tasks["tasks"]:
            task_uri = task["namespace"]
            r = get_task_metrics_from_uri(task_uri)

            # Write the file on disk
            file_path = f"metric_{'_'.join(task_uri.split('.'))}.json"
            with open(file_path, "w") as metric_file:
                metric_file.write(r.text)
            LOGGER.info(f"Metrics saved to {file_path!r}")

        for namespace in get_namespaces(index, index_uri):
            new_uri = uri.copy()
            new_uri.append(namespace["name"])

            if not is_later_or_equal(new_uri, from_date):
                LOGGER.debug("NEW URI %s is before %s", new_uri, from_date)
                continue

            # Temp
            if new_uri not in uris:
                uris.append(new_uri)


def main():
    description = "Retrieve a model training metrics"
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument("model", help="Which model to retrieve training metrics from.")
    parser.add_argument(
        "date",
        nargs="?",
        help="Which date should we retrieve training metrics from. Default to latest",
    )

    args = parser.parse_args()

    get_task_metrics_from_date(args.model, args.date)


if __name__ == "__main__":
    main()
