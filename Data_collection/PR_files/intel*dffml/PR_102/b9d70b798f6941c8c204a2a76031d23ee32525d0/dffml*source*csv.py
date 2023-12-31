# SPDX-License-Identifier: MIT
# Copyright (c) 2019 Intel Corporation
"""
Loads repos from a csv file, using columns as features
"""
import csv
import ast

from ..repo import Repo
from .memory import MemorySource
from .file import FileSource, FileSourceConfig
from typing import NamedTuple, Dict
from ..util.cli.arg import Arg

csv.register_dialect("strip", skipinitialspace=True)


class CSVSourceConfig(FileSourceConfig, NamedTuple):
    filename: str
    label: str = "unlabeled"
    readonly: bool = False
    key: str = None


class CSVSource(FileSource, MemorySource):
    """
    Uses a CSV file as the source of repo feature data
    """

    # Headers we've added to track data other than feature data for a repo
    CSV_HEADERS = ["prediction", "confidence", "classification"]

    @classmethod
    def args(cls, args, *above) -> Dict[str, Arg]:
        cls.config_set(args, above, "key", Arg(type=str, default=None))
        return args

    @classmethod
    def config(cls, config, *above):
        return CSVSourceConfig(
            filename=cls.config_get(config, above, "filename"),
            readonly=cls.config_get(config, above, "readonly"),
            label=cls.config_get(config, above, "label"),
            key=cls.config_get(config, above, "key"),
        )

    async def load_fd(self, fd):
        """
        Parses a CSV stream into Repo instances
        """
        i = 0
        self.mem = {}
        for data in csv.DictReader(fd, dialect="strip"):
            # Repo data we are going to parse from this row (must include
            # features).
            repo_data = {"features": {}}
            # Parse headers we as the CSV source added
            csv_meta = {}
            for header in self.CSV_HEADERS:
                if not data.get(header) is None and data[header] != "":
                    csv_meta[header] = data[header]
                    # Remove from feature data
                    del data[header]
            # Parse feature data
            for key, value in data.items():
                if value != "":
                    try:
                        repo_data["features"][key] = ast.literal_eval(value)
                    except (SyntaxError, ValueError):
                        repo_data["features"][key] = value
                if self.config.key is not None and self.config.key == key:
                    src_url = value
                if self.config.key is None:
                    src_url = str(i)
            i += 1
            # Correct types and structure of repo data from csv_meta
            if "classification" in csv_meta:
                repo_data.update(
                    {"classification": str(csv_meta["classification"])}
                )
            if "prediction" in csv_meta and "confidence" in csv_meta:
                repo_data.update(
                    {
                        "prediction": {
                            "classification": str(csv_meta["prediction"]),
                            "confidence": float(csv_meta["confidence"]),
                        }
                    }
                )
            repo = Repo(src_url, data=repo_data)
            self.mem[repo.src_url] = repo
        self.logger.debug("%r loaded %d records", self, len(self.mem))

    async def dump_fd(self, fd):
        """
        Dumps data into a CSV stream
        """
        # Sample some headers without iterating all the way through
        fieldnames = []
        for repo in self.mem.values():
            fieldnames = list(repo.data.features.keys())
            break
        # Add our headers
        fieldnames += self.CSV_HEADERS
        # Write out the file
        writer = csv.DictWriter(fd, fieldnames=fieldnames)
        writer.writeheader()
        # Write out rows in order
        for repo in self.mem.values():
            repo_data = repo.dict()
            row = {}
            for key, value in repo_data["features"].items():
                row[key] = value
            if "classification" in repo_data:
                row["classification"] = repo_data["classification"]
            if "prediction" in repo_data:
                row["prediction"] = repo_data["prediction"]["classification"]
                row["confidence"] = repo_data["prediction"]["confidence"]
            writer.writerow(row)
        self.logger.debug("%r saved %d records", self, len(self.mem))
