from datetime import date, datetime
import typing
from collections.abc import Callable

import typing_extensions

from gyver.attrs.field import Field, FieldInfo, info
from gyver.attrs.methods import MethodBuilder, MethodType
from gyver.attrs.resolver import FieldsBuilder
from gyver.attrs.utils.functions import frozen as freeze
from gyver.attrs.converters.utils import deserialize_mapping, deserialize
from gyver.attrs.utils.typedef import MISSING, Descriptor, InitOptions

T = typing.TypeVar("T")

Fields = typing.Sequence[Field]


@typing.overload
def define(
    maybe_cls: None = None,
    /,
    *,
    frozen: bool = True,
    slots: bool = True,
    repr: bool = True,
) -> Callable[[type[T]], type[T]]:
    ...


@typing.overload
def define(
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = True,
    slots: bool = True,
    repr: bool = True,
) -> type[T]:
    ...


@typing_extensions.dataclass_transform(
    order_default=True,
    frozen_default=True,
    kw_only_default=False,
    field_specifiers=(FieldInfo, info),
)
def define(
    maybe_cls: typing.Optional[type[T]] = None,
    /,
    *,
    frozen: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
) -> typing.Union[Callable[[type[T]], type[T]], type[T]]:
    def wrap(cls: type[T]) -> type[T]:
        fields = FieldsBuilder(cls, kw_only).from_annotations().build()
        field_map = {field.name: field for field in fields}
        clsdict = (
            _get_clsdict(cls, field_map)
            | _get_cls_metadata(cls)
            | _get_init(cls, field_map, {"frozen": frozen, "slots": slots})
            | _get_parse_dict(cls, field_map)
            | _get_gserialize(cls, field_map)
        )
        if slots:
            clsdict |= _get_slots_metadata(cls, field_map)
        if repr:
            clsdict |= _get_repr(cls, field_map)
        if eq:
            clsdict |= _get_eq(cls, field_map)
        maybe_freeze = freeze if frozen else lambda a: a
        _get_gserialize(cls, field_map)
        return maybe_freeze(type(cls)(cls.__name__, cls.__bases__, clsdict))

    return wrap(maybe_cls) if maybe_cls is not None else wrap


def _get_clsdict(cls: type, field_map: dict[str, Field]):
    return {
        key: value
        for key, value in cls.__dict__.items()
        if key not in (tuple(field_map) + ("__dict__", "__weakref__"))
    } | {"__gyver_attrs__": field_map}


def _get_slots_metadata(
    cls: type,
    field_map: dict[str, Field],
) -> typing.Mapping[str, typing.Any]:
    inherited_slots = {}
    for base_cls in cls.mro()[1:-1]:
        inherited_slots |= {
            name: getattr(base_cls, name)
            for name in getattr(base_cls, "__slots__", ())
        }
    reused_slots = {
        slot: descriptor
        for slot, descriptor in inherited_slots.items()
        if slot in field_map
    }
    slot_names = tuple(
        field for field in field_map if field not in reused_slots
    )
    for value in cls.__dict__.values():
        if _is_descriptor_type(value):
            slot_names += (value.private_name,)
    return inherited_slots | reused_slots | {"__slots__": tuple(slot_names)}


def _is_descriptor_type(
    obj: typing.Any,
) -> typing_extensions.TypeGuard[Descriptor]:
    return hasattr(obj, "private_name") and hasattr(obj, "__get__")


def _get_cls_metadata(cls: type):
    return {"__qualname__": cls.__qualname__}


def _make_setattr(frozen: bool):
    def _setattr(field: str, arg: typing.Any):
        return (
            f"_setattr(self, '{field}', {arg})"
            if frozen
            else f"self.{field} = {arg}"
        )

    return _setattr


def _get_init(cls: type, field_map: dict[str, Field], opts: InitOptions):
    builder = MethodBuilder(
        "__init__",
        {
            "attr_dict": field_map,
            "MISSING": MISSING,
            "_setattr": object.__setattr__,
        },
    )
    _setattr = _make_setattr(opts["frozen"])
    if hasattr(cls, "__pre_init__"):
        builder.add_scriptline("self.__pre_init__()")
    if not opts["slots"]:
        builder.add_scriptline("_inst_dict = self.__dict__")
    for field in field_map.values():
        field_name = field.name
        arg_name = field.alias.lstrip("_")
        if field.has_default:
            arg = f"{arg_name}=attr_dict['{field_name}'].default"

            builder.add_scriptline(_setattr(field_name, arg_name))
        elif field.has_default_factory:
            arg = f"{arg_name}=MISSING"

            init_factory_name = f"__attr_factory_{field_name}"
            for line in (
                f"if {arg_name} is not MISSING:",
                f"    {_setattr(field_name, arg_name)}",
                "else:",
                f'    {_setattr(field_name, f"{init_factory_name}()")}',
            ):
                builder.add_scriptline(line)
            builder.add_glob(init_factory_name, field.default)
        else:
            builder.add_scriptline(_setattr(field_name, arg_name))
            arg = arg_name
        if field.kw_only:
            builder.add_funckarg(arg)
        else:
            builder.add_funcarg(arg)
        builder.add_annotation(arg_name, field.declared_type)
    if hasattr(cls, "__post_init__"):
        builder.add_scriptline("self.__post_init__()")
    return builder.build(cls)


def _get_repr(cls: type, field_map: dict[str, Field]):
    fieldstr = ", ".join(
        f"{field.name}={{self.{field.name}!r}}" for field in field_map.values()
    )
    returnline = f"return f'{cls.__name__}({fieldstr})'"
    return (
        MethodBuilder(
            "__repr__",
        )
        .add_annotation("return", str)
        .add_scriptline(returnline)
        .build(cls)
    )


def _get_eq(cls: type, field_map: dict[str, Field]):
    fields_to_compare = {
        name: field for name, field in field_map.items() if field.eq
    }
    fieldstr = (
        "("
        + ", ".join(f"{{target}}.{name}" for name in fields_to_compare)
        + ")"
    )
    othername = "other"
    returnline = (
        f"return {fieldstr.format(target='self')} "
        f"== {fieldstr.format(target=othername)}"
    )
    return (
        MethodBuilder("__eq__")
        .add_scriptline(returnline)
        .add_funcarg(othername)
        .add_annotation("return", bool)
        .add_annotation("othername", cls)
        .build(cls)
    )


def _get_parse_dict(cls: type, field_map: dict[str, Field]):
    args = []
    alias_args = []
    builder = (
        MethodBuilder(
            "__parse_dict__",
            {
                "deserialize": deserialize,
                "deserialize_mapping": deserialize_mapping,
            },
        )
        .add_funcarg("alias")
        .add_annotation("alias", bool)
        .add_annotation("return", typing.Mapping[str, typing.Any])
    )
    for name, field in field_map.items():
        field_type = field.origin or field.declared_type
        if isinstance(field_type, str):
            raise NotImplementedError(
                "For now gyver-attrs cannot deal correctly"
                " with forward references"
            )
        builder.add_glob(f"field_type_{field.name}", field_type)
        if hasattr(field_type, "__parse_dict__"):
            arg = f"'{{name}}': self.{name}.__parse_dict__(alias)"
        elif issubclass(field_type, (list, tuple, set, dict)):
            arg = _get_parse_dict_sequence_arg(field)
        else:
            arg = f"'{{name}}': self.{name}"
        args.append(arg.format(name=name))
        alias_args.append(arg.format(name=field.alias))
    builder.add_scriptline(
        "\n    ".join(
            (
                "if alias:",
                f"    return {{{', '.join(alias_args)}}}",
                f"return {{{', '.join(args)}}}",
            )
        )
    )
    return builder.build(cls)


def _get_parse_dict_sequence_arg(field: Field) -> str:
    field_type = field.origin or field.declared_type
    if not field.args:
        return f"'{{name}}': self.{field.name}"
    if (
        len(field.args) > 1
        and issubclass(field_type, tuple)
        and (len(field.args) != 2 or field.args[1] is not Ellipsis)
    ):
        idx_to_parse = [
            idx
            for idx, item in enumerate(field.args)
            if hasattr(item, "__parse_dict__")
        ]
        if not idx_to_parse:
            return f"'{{name}}': self.{field.name}"
        tuple_args = ", ".join(
            f"self.{field.name}[{idx}]"
            if idx not in idx_to_parse
            else f"self.{field.name}[{idx}].__parse_dict__(alias)"
            for idx, _ in enumerate(field.args)
        )
        return f"'{{name}}': ({tuple_args})"
    elif len(field.args) == 1 or issubclass(field_type, tuple):
        (element_type, *_) = field.args
        if hasattr(element_type, "__parse_dict__"):
            return (
                f"'{{name}}': field_type_{field.name}(x.__parse_dict__(alias)"
                f" for x in self.{field.name})"
            )
        return f"'{{name}}': deserialize(self.{field.name}, alias)"
    elif issubclass(field_type, typing.Mapping):
        return f"'{{name}}': deserialize_mapping(self.{field.name}, alias)"
    else:
        return f"'{{name}}': deserialize(self.{field.name}, alias)"


def _get_gserialize(cls: type, field_map: dict[str, Field]):
    args = []
    builder = (
        MethodBuilder(
            "__gserialize__",
            {
                "dict_get": dict.get,
            },
        )
        .add_funcarg("mapping")
        .add_annotation("return", cls)
        .add_annotation("mapping", typing.Mapping[str, typing.Any])
        .set_type(MethodType.CLASS)
    )
    for field in field_map.values():
        field_type = field.origin or field.declared_type
        builder.add_glob(f"_field_type_{field.name}", field_type)
        if hasattr(field_type, "__gserialize__"):
            arg = (
                f"_field_type_{field.name}.__gserialize__"
                f"(dict_get(mapping, '{field.alias}')"
                f" or mapping['{field.name}'])"
            )
        elif field_type in (date, datetime):
            arg = (
                f"_field_type_{field.name}.fromisoformat"
                f"(dict_get(mapping, '{field.alias}')"
                f" or mapping['{field.name}'])"
            )
        elif issubclass(field_type, (list, tuple, set, dict)):
            arg, globs = _get_gserialize_sequence_arg(field)
            builder.merge_globs(globs)
        else:
            arg = (
                f"(dict_get(mapping, '{field.alias}')"
                f" or mapping['{field.name}'])"
            )
        args.append(f"{field.alias}={arg}")
    builder.add_scriptline(f"return cls({', '.join(args)})")
    return builder.build(cls)


def _get_gserialize_sequence_arg(
    field: Field,
) -> tuple[str, typing.Mapping[str, typing.Any]]:
    field_type = field.origin or field.declared_type
    globs = {}
    default_line = (
        f"(dict_get(mapping, '{field.alias}')" f" or mapping['{field.name}'])"
    )

    returnline = default_line
    if not field.args:
        pass
    elif (
        len(field.args) > 1
        and issubclass(field_type, tuple)
        and (len(field.args) != 2 or field.args[1] is not Ellipsis)
    ):
        if idx_to_parse := [
            idx
            for idx, item in enumerate(field.args)
            if hasattr(item, "__gserialize__")
        ]:
            for idx in idx_to_parse:
                globs[f"_elem_type_{field.name}_{idx}"] = field.args[idx]
            tuple_args = ", ".join(
                f"{default_line}[{idx}]"
                if idx not in idx_to_parse
                else f"_elem_type_{field.name}_{idx}."
                f"__gserialize__({default_line}[{idx}])"
                for idx, _ in enumerate(field.args)
            )
            returnline = f"({tuple_args})"
    elif len(field.args) == 1 or issubclass(field_type, tuple):
        (element_type, *_) = field.args
        if hasattr(element_type, "__gserialize__"):
            globs[f"_elem_type_{field.name}"] = element_type
            returnline = (
                f"field_type_{field.name}("
                f"_elem_type_{field.name}.__gserialize__(x)"
                f" for x in {default_line})"
            )
    return returnline, globs
