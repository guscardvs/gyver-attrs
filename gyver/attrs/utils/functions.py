import re
from typing import Any, TypeVar, get_args, get_origin

from .typedef import DisassembledType

T = TypeVar("T")


def disassemble_type(typ: type) -> DisassembledType:
    return DisassembledType(typ, get_origin(typ), get_args(typ))


def frozen_setattr(self, name: str, value: Any):
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


def implements(cls: type, name: str):
    attr = getattr(cls, name, _sentinel)
    if attr is _sentinel:
        return False

    return next(
        (False for base_cls in cls.mro()[1:] if getattr(base_cls, name, None) is attr),
        True,
    )


_to_camel_regex = re.compile("_([a-zA-Z])")


def to_camel(string: str) -> str:
    return _to_camel_regex.sub(lambda match: match[1].upper(), string.strip("_"))


def to_upper_camel(string: str) -> str:
    result = to_camel(string)
    return result[:1].upper() + result[1:]
