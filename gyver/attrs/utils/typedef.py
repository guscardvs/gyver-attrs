import typing
from collections.abc import Sequence
from dataclasses import dataclass, field


class DisassembledType(typing.NamedTuple):
    type_: type
    origin: typing.Optional[type]
    args: Sequence[type]
    type_vars: Sequence['TypeNode']
    typenode: 'TypeNode'


@dataclass
class TypeNode:
    type_: typing.Any
    args: list['TypeNode'] = field(default_factory=list)

    def __hash__(self) -> int:
        return id(self)


class MISSING:
    pass


class Descriptor(typing.Protocol):
    private_name: str


class InitOptions(typing.TypedDict):
    slots: bool
    frozen: bool
    init: bool


class UNINITIALIZED:
    pass
