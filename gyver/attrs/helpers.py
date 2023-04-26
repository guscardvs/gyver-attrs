from functools import wraps
from typing import Any, Callable, TypeVar, cast

from typing_extensions import Concatenate, ParamSpec

from .field import Field

T = TypeVar("T")
R = TypeVar("R")
P = ParamSpec("P")


def validate_type(
    func: Callable[Concatenate[T, P], R]
) -> Callable[Concatenate[T, P], R]:
    @wraps(func)
    def inner(obj: T, *args: P.args, **kwargs: P.kwargs) -> R:
        if not hasattr(obj, "__gyver_attrs__"):
            raise TypeError(f"Type {obj} is not defined by gyver-attrs", obj)
        return func(obj, *args, **kwargs)

    return inner


@validate_type
def fields(cls: type) -> dict[str, Field]:
    """Returns the fields used to build the class
    by dict[name, Field]"""
    return getattr(cls, "__gyver_attrs__")


@validate_type
def call_init(self: Any, *args, **kwargs) -> None:
    """Calls __gattrs_init__ without having redlines in the code"""
    init = cast(
        Callable[..., None],
        getattr(self, "__gattrs_init__", getattr(self, "__init__")),
    )
    return init(*args, **kwargs)
