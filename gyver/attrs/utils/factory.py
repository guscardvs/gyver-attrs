import typing

from typing_extensions import ParamSpec

P = ParamSpec("P")
T = typing.TypeVar("T")


class Factory(typing.Generic[P, T]):
    __slots__ = ("func",)

    def __init__(self, func: typing.Callable[P, T]) -> None:
        self.func = func

    def __call__(self, *args: P.args, **kwds: P.kwargs) -> T:
        return self.func(*args, **kwds)

    @property
    def __name__(self):
        return self.func.__name__


def mark_factory(func: typing.Callable[P, T]) -> Factory[P, T]:
    return Factory(func)


def is_factory_marked(obj: typing.Any) -> bool:
    return isinstance(obj, Factory)
