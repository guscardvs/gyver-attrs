from typing import Any, Optional, Sequence
from gyver.attrs.utils.typedef import MISSING, DisassembledType
from gyver.attrs.utils.factory import is_factory_marked


class Field:
    __slots__ = ("name", "type_", "kw_only", "default", "alias")

    def __init__(
        self,
        name: str,
        type_: DisassembledType,
        kw_only: bool,
        default: Any,
        alias: str,
    ) -> None:
        self.name = name
        self.type_ = type_
        self.kw_only = kw_only
        self.default = default
        self.alias = alias

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
    def has_default(self) -> bool:
        return self.default is not MISSING and not is_factory_marked(
            self.default
        )

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
                    f"type={self.type_}",
                    f"default={default_name}",
                    f"kw_only={self.kw_only}",
                    f"alias={self.alias}",
                )
            )
            + ")"
        )


class FieldInfo:
    __slots__ = ("default", "kw_only", "alias")

    def __init__(
        self,
        default: Any,
        alias: str,
        kw_only: bool,
    ) -> None:
        self.default = default
        self.kw_only = kw_only
        self.alias = alias


def info(
    default: Any = ...,
    alias: str = "",
    kw_only: bool = False,
) -> Any:
    return FieldInfo(
        default if default is not Ellipsis else MISSING, alias, kw_only
    )
