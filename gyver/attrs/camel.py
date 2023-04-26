from typing import Any, Callable, Literal, Optional, TypeVar, Union, overload

import typing_extensions

from gyver.attrs.main import define

from .field import Field, FieldInfo, info
from .utils.functions import to_camel, to_upper_camel
from .utils.typedef import DisassembledType

T = TypeVar("T")


class ToCamelField(Field):
    def __init__(
        self,
        name: str,
        type_: DisassembledType,
        kw_only: bool,
        default: Any,
        alias: str,
        eq: Union[bool, Callable[[Any], Any]],
        order: Union[bool, Callable[[Any], Any]],
        inherited: bool = False,
    ) -> None:
        super().__init__(
            name,
            type_,
            kw_only,
            default,
            alias if alias != name else to_camel(name),
            eq,
            order,
            inherited,
        )


class ToUpperCamelField(Field):
    def __init__(
        self,
        name: str,
        type_: DisassembledType,
        kw_only: bool,
        default: Any,
        alias: str,
        eq: Union[bool, Callable[[Any], Any]],
        order: Union[bool, Callable[[Any], Any]],
        inherited: bool = False,
    ) -> None:
        super().__init__(
            name,
            type_,
            kw_only,
            default,
            alias if alias != name else to_upper_camel(name),
            eq,
            order,
            inherited,
        )


@overload
def define_camel(
    maybe_cls: None = None,
    /,
    *,
    style: Literal["upper", "lower"] = "lower",
    frozen: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = False,
) -> Callable[[type[T]], type[T]]:
    ...


@overload
def define_camel(
    maybe_cls: type[T],
    /,
    *,
    style: Literal["upper", "lower"] = "lower",
    frozen: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = False,
) -> type[T]:
    ...


@typing_extensions.dataclass_transform(
    order_default=True,
    frozen_default=True,
    kw_only_default=False,
    field_specifiers=(FieldInfo, info),
)
def define_camel(
    maybe_cls: Optional[type[T]] = None,
    /,
    *,
    style: Literal["upper", "lower"] = "lower",
    frozen: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: Optional[bool] = None,
    pydantic: bool = True,
    dataclass_fields: bool = False,
) -> Union[Callable[[type[T]], type[T]], type[T]]:
    field_class = ToCamelField if style == "lower" else ToUpperCamelField
    return define(
        maybe_cls,
        frozen=frozen,
        kw_only=kw_only,
        slots=slots,
        repr=repr,
        eq=eq,
        order=order,
        hash=hash,
        pydantic=pydantic,
        dataclass_fields=dataclass_fields,
        field_class=field_class,
    )
