from unittest.mock import patch
from typing import NamedTuple

from dffml.util.cli.plugin import Plugin, parse_unknown
from dffml.util.entrypoint import entrypoint
from dffml.df.base import BaseKeyValueStore, BaseRedundancyCheckerConfig
from dffml.df.memory import MemoryKeyValueStore, MemoryRedundancyChecker
from dffml.util.asynctestcase import AsyncTestCase


class KeyValueStoreWithArgumentsConfig(NamedTuple):
    filename: str


@entrypoint("withargs")
class KeyValueStoreWithArguments(BaseKeyValueStore):

    CONTEXT = NotImplementedError

    def __call__(self):
        raise NotImplementedError

    @classmethod
    def args(cls, args, *above):
        cls.config_set(args, above, "filename", Plugin(type=str))
        return args

    @classmethod
    def config(cls, config, *above):
        return KeyValueStoreWithArgumentsConfig(
            filename=cls.config_get(config, above, "filename")
        )


def load_kvstore_with_args(loading=None):
    if loading == "withargs":
        return KeyValueStoreWithArguments
    return [KeyValueStoreWithArguments]


class TestMemoryRedundancyChecker(AsyncTestCase):
    @patch.object(BaseKeyValueStore, "load", load_kvstore_with_args)
    def test_args(self):
        self.assertEqual(
            MemoryRedundancyChecker.args({}),
            {
                "rchecker": {
                    "plugin": None,
                    "config": {
                        "memory": {
                            "plugin": None,
                            "config": {
                                "kvstore": {
                                    "plugin": Plugin(
                                        type=BaseKeyValueStore.load,
                                        default=MemoryKeyValueStore,
                                    ),
                                    "config": {
                                        "withargs": {
                                            "plugin": None,
                                            "config": {
                                                "filename": {
                                                    "plugin": Plugin(type=str),
                                                    "config": {},
                                                }
                                            },
                                        }
                                    },
                                }
                            },
                        }
                    },
                }
            },
        )

    @patch.object(BaseKeyValueStore, "load", load_kvstore_with_args)
    def test_config_default_label(self):
        was = MemoryRedundancyChecker.config(
            parse_unknown(
                "--rchecker-memory-kvstore",
                "withargs",
                "--rchecker-memory-kvstore-withargs-filename",
                "somefile",
            )
        )
        self.assertEqual(type(was), BaseRedundancyCheckerConfig)
        self.assertEqual(type(was.key_value_store), KeyValueStoreWithArguments)
        self.assertEqual(
            type(was.key_value_store.config), KeyValueStoreWithArgumentsConfig
        )
        self.assertEqual(was.key_value_store.config.filename, "somefile")
