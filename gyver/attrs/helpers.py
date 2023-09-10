from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable, Sequence, TypeVar, cast

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


CallbackSequence = Sequence[Callable[[T], Any]]


def null_callable():
    pass


@contextmanager
@validate_type
def init_hooks(
    self: T,
    pre_callbacks: CallbackSequence[T] = (),
    post_callbacks: CallbackSequence[T] = (),
):
    pre_init = getattr(self, "__pre_init__", null_callable)
    post_init = getattr(self, "__post_init__", null_callable)

    for call in pre_callbacks:
        call(self)
    pre_init()
    yield
    for call in post_callbacks:
        call(self)
    post_init()
