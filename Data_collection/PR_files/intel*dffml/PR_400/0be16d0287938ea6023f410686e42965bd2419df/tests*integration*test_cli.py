"""
This file contains integration tests. We use the CLI to exercise functionality of
various DFFML classes and constructs.
"""
import re
import os
import io
import json
import inspect
import pathlib
import asyncio
import contextlib
import unittest.mock
from typing import Dict, Any

from dffml.record import Record
from dffml.base import config
from dffml.df.types import Definition, Operation, DataFlow, Input
from dffml.df.base import op
from dffml.cli.cli import CLI
from dffml.model.model import Model
from dffml.service.dev import Develop
from dffml.util.packaging import is_develop
from dffml.util.entrypoint import load
from dffml.config.config import BaseConfigLoader
from dffml.util.asynctestcase import AsyncTestCase, IntegrationCLITestCase


class TestList(IntegrationCLITestCase):
    async def test_records(self):
        keys = ["A", "B", "C"]
        with contextlib.redirect_stdout(self.stdout):
            await CLI.cli(
                "list",
                "records",
                "-sources",
                "feed=memory",
                "-source-records",
                *keys,
            )
        stdout = self.stdout.getvalue()
        for key in keys:
            self.assertIn(key, stdout)


class TestMerge(IntegrationCLITestCase):
    async def test_memory_to_json(self):
        keys = ["A", "B", "C"]
        filename = self.mktempfile()
        await CLI.cli(
            "merge",
            "dest=json",
            "src=memory",
            "-source-dest-filename",
            filename,
            "-source-src-records",
            *keys,
            "-source-src-allowempty",
            "-source-dest-allowempty",
            "-source-src-readwrite",
            "-source-dest-readwrite",
        )
        with contextlib.redirect_stdout(self.stdout):
            await CLI.cli(
                "list",
                "records",
                "-sources",
                "tmp=json",
                "-source-tmp-filename",
                filename,
            )
        stdout = self.stdout.getvalue()
        for key in keys:
            self.assertIn(key, stdout)

    async def test_memory_to_csv(self):
        keys = ["A", "B", "C"]
        filename = self.mktempfile()
        await CLI.cli(
            "merge",
            "dest=csv",
            "src=memory",
            "-source-dest-filename",
            filename,
            "-source-src-records",
            *keys,
            "-source-src-allowempty",
            "-source-dest-allowempty",
            "-source-src-readwrite",
            "-source-dest-readwrite",
        )
        self.assertEqual(
            pathlib.Path(filename).read_text(),
            inspect.cleandoc(
                """
                key,tag
                A,untagged
                B,untagged
                C,untagged
                """
            )
            + "\n",
        )
