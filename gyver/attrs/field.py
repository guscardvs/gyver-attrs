from typing import Any, Callable, Optional, Sequence, Union, overload

from typing_extensions import Self

from gyver.attrs.utils.factory import is_factory_marked, mark_factory
from gyver.attrs.utils.typedef import MISSING, DisassembledType

BoolOrCallable = Union[bool, Callable[[Any], Any]]


class Field:
    __slots__ = (
        "name",
        "type_",
        "kw_only",
        "default",
        "alias",
        "eq",
        "order",
        "init",
        "hash",
        "repr",
        "asdict_",
        "fromdict",
        "inherited",
    )

    def __init__(
        self,
        name: str,
        type_: DisassembledType,
        kw_only: bool,
        default: Any,
        alias: str,
        eq: BoolOrCallable,
        order: BoolOrCallable,
        init: bool,
        hash: BoolOrCallable,
        repr: Union[bool, Callable[[Any], str]],
        asdict_: Optional[Callable[[Any], Any]],
        fromdict: Optional[Callable[[Any], Any]],
        inherited: bool = False,
    ) -> None:
        self.name = name
        self.type_ = type_
        self.kw_only = kw_only
        self.default = default
        self.alias = alias
        self.eq = eq
        self.order = order
        self.init = init
        self.hash = hash
        self.repr = repr
        self.asdict_ = asdict_
        self.fromdict = fromdict
        self.inherited = inherited

    @property
    def argname(self):
        return self.alias or self.name

    @property
    def has_alias(self) -> bool:
        return self.alias != self.name

    @property
    def origin(self) -> Optional[type]:
        return self.type_.origin

    @property
    def args(self) -> Sequence[type]:
        return self.type_.args

    @property
    def declared_type(self) -> type:
        return self.type_.type_

    @property
    def field_type(self) -> type:
        return self.origin or self.declared_type

    @property
    def has_default(self) -> bool:
        return self.default is not MISSING and not is_factory_marked(self.default)

    @property
    def has_default_factory(self) -> bool:
        return is_factory_marked(self.default)

    @property
    def allow_none(self) -> bool:
        return None in self.args

    def __repr__(self) -> str:
        default_name = (
            self.default.__name__ if self.has_default_factory else self.default
        )
        return "Field(" + (
            ", ".join(
                (
                    f"name={self.name}",
                    f"type_={self.type_}",
                    f"default={default_name}",
                    f"kw_only={self.kw_only}",
                    f"alias={self.alias}",
                    f"eq={self.eq}",
                    f"order={self.order}",
                    f"init={self.init}",
                    f"hash={self.hash}",
                    f"repr={self.repr}",
                    f"asdict_={self.asdict_}",
                    f"inherited={self.inherited}",
                )
            )
            + ")"
        )

    def asdict(self):
        return {key: getattr(self, key) for key in self.__slots__}

    def duplicate(self, **overload):
        return type(self)(**self.asdict() | overload)

    def inherit(self) -> Self:
        return self.duplicate(inherited=True)


class FieldInfo:
    __slots__ = (
        "default",
        "kw_only",
        "alias",
        "eq",
        "order",
        "init",
        "hash",
        "repr",
        "asdict_",
        "fromdict",
    )

    def __init__(
        self,
        default: Any,
        alias: str,
        kw_only: bool,
        eq: BoolOrCallable,
        order: BoolOrCallable,
        init: bool,
        hash: BoolOrCallable,
        repr: Union[bool, Callable[[Any], str]],
        asdict_: Optional[Callable[[Any], Any]],
        fromdict: Optional[Callable[[Any], Any]],
    ) -> None:
        self.default = default
        self.kw_only = kw_only
        self.alias = alias
        self.eq = eq
        self.order = order
        self.init = init
        self.hash = hash
        self.repr = repr
        self.asdict_ = asdict_
        self.fromdict = fromdict

    def asdict(self):
        return {key: getattr(self, key) for key in self.__slots__}

    def duplicate(self, **overload):
        return FieldInfo(**self.asdict() | overload)

    def build(self, field_cls: type[Field], **extras) -> Field:
        return field_cls(**self.asdict() | extras)


@overload
def info(
    *,
    default_factory: Callable[[], Any],
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: Union[bool, Callable[[Any], str]] = True,
    asdict: Optional[Callable[[Any], Any]] = None,
    fromdict: Optional[Callable[[Any], Any]] = None,
) -> Any:  # sourcery skip: instance-method-first-arg-name
    ...


@overload
def info(
    *,
    default: Any,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: Union[bool, Callable[[Any], str]] = True,
    asdict: Optional[Callable[[Any], Any]] = None,
    fromdict: Optional[Callable[[Any], Any]] = None,
) -> Any:  # sourcery skip: instance-method-first-arg-name
    ...


@overload
def info(
    *,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: Union[bool, Callable[[Any], str]] = True,
    asdict: Optional[Callable[[Any], Any]] = None,
    fromdict: Optional[Callable[[Any], Any]] = None,
) -> Any:  # sourcery skip: instance-method-first-arg-name
    ...


def info(
    *,
    default: Any = ...,
    default_factory: Callable[[], Any] = ...,
    alias: str = "",
    kw_only: bool = False,
    eq: BoolOrCallable = True,
    order: BoolOrCallable = True,
    init: bool = True,
    hash: BoolOrCallable = True,
    repr: Union[bool, Callable[[Any], str]] = True,
    asdict: Optional[Callable[[Any], Any]] = None,
    fromdict: Optional[Callable[[Any], Any]] = None,
) -> Any:  # sourcery skip: instance-method-first-arg-name
    """
    Declare metadata for a gyver-attrs field.

    :param default: The default value of the field.
    :param default_factory: A callable that returns the default value of the field.
    :param alias: The alternative name for the field.
    :param kw_only: Whether the field should be a keyword-only parameter in
    the generated constructor.
    :param eq: Whether the field should be used in the equality comparison of instances
    of the class.
               If a callable is passed, it will be used to compare the field values.
    :param order: Whether the field should be used in rich comparison ordering
    of instances of the class.
                 If a callable is passed, it will be used to compare the field values.
    """
    if default_factory is not Ellipsis:
        default = mark_factory(default_factory)
    return FieldInfo(
        default if default is not Ellipsis else MISSING,
        alias,
        kw_only,
        eq,
        order,
        init,
        hash,
        repr,
        asdict,
        fromdict,
    )


default_info: FieldInfo = info()
