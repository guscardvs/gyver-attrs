import typing


class DisassembledType(typing.NamedTuple):
    type_: type
    origin: typing.Optional[type]
    args: typing.Sequence[type]


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
