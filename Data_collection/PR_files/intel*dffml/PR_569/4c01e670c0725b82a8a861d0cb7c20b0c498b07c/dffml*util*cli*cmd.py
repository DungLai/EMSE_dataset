# SPDX-License-Identifier: MIT
# Copyright (c) 2019 Intel Corporation
import sys
import json
import uuid
import enum
import logging
import inspect
import asyncio
import argparse
from typing import Dict, Any
import dataclasses

from ...record import Record
from ...feature import Feature

from ..data import export_dict
from .arg import Arg, parse_unknown
from ...base import config, _fromdict, mkarg, field

DisplayHelp = "Display help message"


class CMDOutputOverride:
    """
    Override dumping of results
    """


if sys.platform == "win32":  # pragma: no cov
    asyncio.set_event_loop(asyncio.ProactorEventLoop())


class ParseLoggingAction(argparse.Action):
    def __call__(self, parser, namespace, value, option_string=None):
        setattr(
            namespace, self.dest, getattr(logging, value.upper(), logging.INFO)
        )
        logging.basicConfig(level=getattr(namespace, self.dest))


class JSONEncoder(json.JSONEncoder):
    """
    Encodes dffml types to JSON representation.
    """

    def default(self, obj):
        typename_lower = str(type(obj)).lower()
        if isinstance(obj, Record):
            return obj.dict()
        elif isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, Feature):
            return obj.name
        elif isinstance(obj, enum.Enum):
            return str(obj.value)
        elif isinstance(obj, type):
            return str(obj.__qualname__)
        elif "numpy." in typename_lower:
            if ".int" in typename_lower or ".uint" in typename_lower:
                return int(obj)
            elif typename_lower.startswith("float"):
                return float(obj)
        elif str(obj).startswith("typing."):
            return str(obj).split(".")[-1]
        return json.JSONEncoder.default(self, obj)


class Parser(argparse.ArgumentParser):
    def add_subs(self, add_from: "CMD"):
        """
        Add sub commands and arguments recursively
        """
        # Only one subparser should be created even if multiple sub commands
        subparsers = None
        # TODO
        # In order to add log to every command we just add it here, first thing
        # self.add_argument("-log", "")
        for name, method in [
            (name.lower().replace("_", ""), method)
            for name, method in inspect.getmembers(add_from)
        ]:
            if inspect.isclass(method) and issubclass(method, CMD):
                if subparsers is None:  # pragma: no cover
                    subparsers = self.add_subparsers()  # pragma: no cover
                parser = subparsers.add_parser(
                    name,
                    description=None
                    if method.__doc__ is None
                    else method.__doc__,
                    formatter_class=getattr(
                        method,
                        "CLI_FORMATTER_CLASS",
                        argparse.ArgumentDefaultsHelpFormatter,
                    ),
                )
                parser.set_defaults(cmd=method)
                parser.set_defaults(parser=parser)
                parser.add_subs(method)  # type: ignore
            elif isinstance(method, Arg):
                try:
                    self.add_argument(method.name, **method)
                except argparse.ArgumentError as error:
                    raise Exception(repr(add_from)) from error

        position_list = {}
        for field in dataclasses.fields(add_from.CONFIG):
            arg = mkarg(field)
            if isinstance(arg, Arg):
                if isinstance(field.metadata.get("position"), int):
                    position_list[field.metadata.get("position")] = (
                        field.name,
                        arg,
                    )
                else:
                    try:
                        self.add_argument(
                            "-" + field.name.replace("_", "-"), **arg
                        )
                    except argparse.ArgumentError as error:
                        raise Exception(repr(add_from)) from error

        if position_list:
            for position in sorted(position_list.keys()):
                name, positional_arg = position_list[position]
                self.add_argument(name.replace("_", "-"), **positional_arg)
            position_list.clear()


@config
class CMDConfig:
    log: str = field(
        "Logging Level",
        default=logging.INFO,
        required=False,
        action=ParseLoggingAction,
    )


class CMD(object):

    JSONEncoder = JSONEncoder
    EXTRA_CONFIG_ARGS = {}
    CONFIG = CMDConfig
    ENTRY_POINT_NAME = ["service"]

    def __init__(self, extra_config=None, **kwargs) -> None:
        if not hasattr(self, "logger"):
            self.logger = logging.getLogger(
                "%s.%s"
                % (self.__class__.__module__, self.__class__.__qualname__)
            )
        if extra_config is None:
            extra_config = {}
        self.extra_config = extra_config

        for field in dataclasses.fields(self.CONFIG):
            arg = mkarg(field)
            if isinstance(arg, Arg):
                if not field.name in kwargs and field.default:
                    kwargs[field.name] = field.default
                if field.name in kwargs and not hasattr(self, field.name):
                    self.logger.debug(
                        "Setting %s = %r", field.name, kwargs[field.name]
                    )
                    setattr(self, field.name, kwargs[field.name])
                else:
                    self.logger.debug("Ignored %s", field.name)

        for name, method in [
            (name.lower().replace("arg_", ""), method)
            for name, method in inspect.getmembers(self)
            if isinstance(method, Arg)
        ]:
            if not name in kwargs and method.name in kwargs:
                name = method.name
            if not name in kwargs and "default" in method:
                kwargs[name] = method["default"]
            if name in kwargs and not hasattr(self, name):
                self.logger.debug("Setting %s = %r", name, kwargs[name])
                setattr(self, name, kwargs[name])
            else:
                self.logger.debug("Ignored %s", name)

    async def __aenter__(self):
        pass

    async def __aexit__(self, exc_type, exc_value, traceback):
        pass

    @classmethod
    async def parse_args(cls, *args):
        parser = Parser(
            description=cls.__doc__,
            formatter_class=getattr(
                cls,
                "CLI_FORMATTER_CLASS",
                argparse.ArgumentDefaultsHelpFormatter,
            ),
        )
        parser.add_subs(cls)
        return parser, parser.parse_known_args(args)

    async def do_run(self):
        async with self:
            if inspect.isasyncgenfunction(self.run):
                return [res async for res in self.run()]
            else:
                return await self.run()

    @classmethod
    async def cli(cls, *args):
        parser, (args, unknown) = await cls.parse_args(*args)
        args.extra_config = parse_unknown(*unknown)
        if (
            getattr(cls, "run", None) is not None
            and getattr(args, "cmd", None) is None
        ):
            args.cmd = cls
        if getattr(args, "cmd", None) is None:
            parser.print_help()
            return DisplayHelp
        if not inspect.isfunction(getattr(args.cmd, "run", None)):
            args.parser.print_help()
            return DisplayHelp
        cmd = args.cmd(**cls.sanitize_args(vars(args)))
        return await cmd.do_run()

    @classmethod
    def sanitize_args(cls, args):
        """
        Remove CMD internals from arguments passed to subclasses of CMD.
        """
        for rm in ["cmd", "parser", "log"]:
            if rm in args:
                del args[rm]
        return args

    @classmethod
    async def _main(cls, *args):
        result = await cls.cli(*args)
        if (
            result is not None
            and result is not DisplayHelp
            and result is not CMDOutputOverride
            and result != [CMDOutputOverride]
        ):
            json.dump(
                export_dict(result=result)["result"],
                sys.stdout,
                sort_keys=True,
                indent=4,
                separators=(",", ": "),
                cls=cls.JSONEncoder,
            )
            print()

    @classmethod
    def main(cls, loop=None, argv=sys.argv):
        """
        Runs cli commands in asyncio loop and outputs in appropriate format
        """
        if loop is None:
            loop = asyncio.get_event_loop()
            # In Python 3.8 ThreadedChildWatcher becomes the default which
            # should work fine for us. However, in Python 3.7 SafeChildWatcher
            # is the default and may cause BlockingIOErrors when many
            # subprocesses are created
            # https://docs.python.org/3/library/asyncio-policy.html#asyncio.FastChildWatcher
            if (
                sys.version_info.major == 3
                and sys.version_info.minor == 7
                and sys.platform != "win32"
            ):
                watcher = asyncio.FastChildWatcher()
                asyncio.set_child_watcher(watcher)
                watcher.attach_loop(loop)
        result = None
        try:
            result = loop.run_until_complete(cls._main(*argv[1:]))
        except KeyboardInterrupt:  # pragma: no cover
            pass  # pragma: no cover
        loop.run_until_complete(loop.shutdown_asyncgens())
        loop.close()

    def __call__(self):
        return asyncio.run(self.do_run())

    @classmethod
    def args(cls, args, *above) -> Dict[str, Any]:
        """
        For compatibility with scripts/docs.py. Nothing else at the moment so if
        it doesn't work with other things that's why.
        """
        return args
