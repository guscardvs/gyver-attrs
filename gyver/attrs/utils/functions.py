import re
from typing import Any, Callable, TypeVar, Union, get_args, get_origin

from .typedef import UNINITIALIZED, DisassembledType

T = TypeVar("T")


def disassemble_type(typ: type) -> DisassembledType:
    return DisassembledType(typ, get_origin(typ), get_args(typ))


def frozen_setattr(self, name: str, value: Any):
    if getattr(self, name, UNINITIALIZED) is UNINITIALIZED:
        return object.__setattr__(self, name, value)
    del value
    raise AttributeError(
        f"Class {type(self)} is frozen, and attribute {name} cannot be set"
    )


def frozen_delattr(self, name: str):
    raise AttributeError(
        f"Class {type(self)} is frozen, and attribute {name} cannot be deleted"
    )


def frozen(cls: type[T]) -> type[T]:
    setattr(cls, "__setattr__", frozen_setattr)
    setattr(cls, "__delattr__", frozen_delattr)
    return cls


def indent(string: str, *, skip_line: bool = False) -> str:
    returnstr = f"    {string}"
    if skip_line:
        returnstr = "\n" + returnstr
    return returnstr


_sentinel = object()


def stamp_func(item: Union[Callable, classmethod, staticmethod]):
    to_stamp = item
    if isinstance(item, (classmethod, staticmethod)):
        to_stamp = item.__func__
    setattr(to_stamp, "__gattrs_func__", True)


def implements(cls: type, name: str):
    attr = getattr(cls, name, _sentinel)
    if attr is _sentinel:
        return False

    if hasattr(attr, "__gattrs_func__"):
        return False

    if func := getattr(attr, "__func__", None):
        if hasattr(func, "__gattrs_func__"):
            return False
    return all(getattr(base_cls, name, None) is not attr for base_cls in cls.mro()[1:])


_to_camel_regex = re.compile("_([a-zA-Z])")


def to_camel(string: str) -> str:
    return _to_camel_regex.sub(lambda match: match[1].upper(), string.strip("_"))


def to_upper_camel(string: str) -> str:
    result = to_camel(string)
    return result[:1].upper() + result[1:]
