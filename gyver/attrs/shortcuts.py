import typing

import typing_extensions

from .field import FieldInfo, info
from .main import define

T = typing.TypeVar("T")

ReturnT = typing.Union[typing.Callable[[type[T]], type[T]], type[T]]
OptionalTypeT = typing.Optional[type[T]]


@typing.overload
def mutable(
    maybe_cls: None = None,
    /,
    *,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = True,
) -> typing.Callable[[type[T]], type[T]]:
    ...


@typing.overload
def mutable(
    maybe_cls: type[T],
    /,
    *,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = True,
) -> type[T]:
    ...


@typing_extensions.dataclass_transform(
    order_default=True,
    frozen_default=False,
    kw_only_default=False,
    field_specifiers=(FieldInfo, info),
)
def mutable(
    maybe_cls: OptionalTypeT[T] = None,
    /,
    *,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = True,
) -> ReturnT[T]:
    return define(
        maybe_cls,
        frozen=False,
        kw_only=kw_only,
        slots=slots,
        repr=repr,
        eq=eq,
        order=order,
        hash=hash,
        pydantic=pydantic,
        dataclass_fields=dataclass_fields,
    )


@typing.overload
def kw_only(
    maybe_cls: None = None,
    /,
    *,
    frozen: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = True,
) -> typing.Callable[[type[T]], type[T]]:
    ...


@typing.overload
def kw_only(
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = True,
) -> type[T]:
    ...


@typing_extensions.dataclass_transform(
    order_default=True,
    frozen_default=True,
    kw_only_default=True,
    field_specifiers=(FieldInfo, info),
)
def kw_only(
    maybe_cls: OptionalTypeT[T] = None,
    /,
    *,
    frozen: bool = True,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = True,
) -> ReturnT[T]:
    return define(
        maybe_cls,
        frozen=frozen,
        kw_only=True,
        slots=slots,
        repr=repr,
        eq=eq,
        order=order,
        hash=hash,
        pydantic=pydantic,
        dataclass_fields=dataclass_fields,
    )


@typing.overload
def schema_class(
    maybe_cls: None = None,
    /,
    *,
    frozen: bool = False,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    dataclass_fields: bool = True,
) -> typing.Callable[[type[T]], type[T]]:
    ...


@typing.overload
def schema_class(
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = False,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    dataclass_fields: bool = True,
) -> type[T]:
    ...


@typing_extensions.dataclass_transform(
    order_default=True,
    frozen_default=True,
    kw_only_default=False,
    field_specifiers=(FieldInfo, info),
)
def schema_class(
    maybe_cls: OptionalTypeT[T] = None,
    /,
    *,
    frozen: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    dataclass_fields: bool = True,
) -> ReturnT[T]:
    return define(
        maybe_cls,
        frozen=frozen,
        kw_only=kw_only,
        slots=slots,
        repr=repr,
        eq=eq,
        order=order,
        hash=hash,
        pydantic=True,
        dataclass_fields=dataclass_fields,
    )
