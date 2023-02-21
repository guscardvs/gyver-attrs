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


def indent(string: str, *, skip_line: bool) -> str:
    returnstr = f"    {string}"
    if skip_line:
        returnstr = "\n" + returnstr
    return returnstr
