"""
Various helper functions for manipulating python data structures and values
"""

import inspect
import pydoc
import inspect
from functools import wraps
import pathlib
from typing import Callable


def merge(one, two):
    for key, value in two.items():
        if key in one and isinstance(value, dict):
            merge(one[key], two[key])
        else:
            one[key] = two[key]


def traverse_config_set(target, *args):
    """
    >>> traverse_set({'level': {'one': 1}}, 'level', 'one', 42)
    {'level': {'one': 42}}
    """
    # Seperate the path down from the value to set
    path, value = args[:-1], args[-1]
    current = target
    last = target
    for level in path:
        if not level in current:
            current[level] = {"arg": None, "config": {}}
        last = current[level]
        current = last["config"]
    last["arg"] = value
    return target


def traverse_config_get(target, *args):
    """
    >>> traverse_set({'level': {'one': 1}}, 'level', 'one', 42)
    {'level': {'one': 42}}
    """
    current = target
    last = target
    for level in args:
        last = current[level]
        current = last["config"]
    return last["arg"]


def traverse_get(target, *args):
    """
    Travel down through a dict
    >>> traverse_get({"one": {"two": 3}}, ["one", "two"])
    3
    """
    current = target
    for level in args:
        current = current[level]
    return current


def traverse_set(target, *args):
    """
    >>> traverse_set({"one": {"two": 3}}, ["one", "two"])
    """


def ignore_args(func):
    """
    Decorator to call the decorated function without any arguments passed to it.
    """

    @wraps(func)
    def wrapper(*_args, **_kwargs):
        return func()

    return wrapper


# STANDARD_TYPES Will be the type names which are applicable across languages
# used to transform types from one language into anothers
STANDARD_TYPES = {"Dict": "map", "List": "array", "Any": "generic"}
STANDARD_TYPES_REVERSED = dict(
    zip(STANDARD_TYPES.values(), STANDARD_TYPES.keys())
)


def type_lookup(typename):
    if typename in STANDARD_TYPES_REVERSED:
        typename = f"typing.{STANDARD_TYPES_REVERSED[typename]}"
    # TODO(security) Make sure pydoc.locate won't blow up in our face ever
    typeof = pydoc.locate(typename)
    if typeof is None:
        raise TypeError(typename)
    return typeof


def export_value(obj, key, value):
    # export and _asdict are not classmethods
    if inspect.isclass(value):
        obj[key] = value.__qualname__
    elif hasattr(value, "export"):
        obj[key] = value.export()
    elif hasattr(value, "_asdict"):
        obj[key] = value._asdict()
    elif getattr(value, "__module__", None) == "typing":
        obj[key] = STANDARD_TYPES.get(
            str(value).replace("typing.", ""), "generic"
        )


def export_list(iterable):
    for i, value in enumerate(iterable):
        export_value(iterable, i, value)
        if isinstance(iterable[i], dict):
            iterable[i] = export_dict(**iterable[i])
        elif isinstance(value, list):
            iterable[i] = export_list(iterable[i])
    return iterable


def export_dict(**kwargs):
    """
    Return the dict given as kwargs but first recurse into each element and call
    its export or _asdict function if it is not a serializable type.
    """
    for key, value in kwargs.items():
        export_value(kwargs, key, value)
        if isinstance(kwargs[key], dict):
            kwargs[key] = export_dict(**kwargs[key])
        elif isinstance(kwargs[key], list):
            kwargs[key] = export_list(kwargs[key])
    return kwargs


def explore_directories(path_dict: dict):
    """
    Recursively explores any path binded to a key in `path_dict`

    eg:
        | root
            |deadbeef
                |file1.txt
                |colosseum
                    | battle.rst
            |face
                |file2.jpg

        >>>explore_directories(path_dict ={
                "hello":"there",
                "deadbeef" : path_to_deadbeef
                })

            {
                "hello":"there",
                "deadbeef":{
                    "file1" : path_to_file1.txt
                    "colosseum":{
                        "battle":path_to_battle.rst
                    }
                }
                "face":{
                    "file2":path_to_file2.txt
                }
            }
    """
    for key, val in path_dict.items():
        t_path = pathlib.Path(val)
        if t_path.is_dir():
            temp_path_dict = {}
            for _path in pathlib.Path(val).glob("*"):
                t_path = pathlib.Path(_path)
                temp_path_dict[t_path.stem] = _path
            explore_directories(temp_path_dict)
            path_dict[key] = temp_path_dict
    return path_dict


async def nested_apply(target: dict, func: Callable):
    """
    Applies `func` recursively to all non dict types in `target`
    """
    for key, val in target.items():
        if isinstance(val, dict):
            target[key] = await nested_apply(val, func)
        else:
            if inspect.iscoroutinefunction(func):
                target[key] = await func(val)
            else:
                target[key] = func(val)
    return target
