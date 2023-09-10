import dataclasses
import typing
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from enum import Enum

import typing_extensions

from gyver.attrs import schema
from gyver.attrs.converters.utils import deserialize, deserialize_mapping, fromdict
from gyver.attrs.field import Field, FieldInfo, info
from gyver.attrs.methods import MethodBuilder, MethodType
from gyver.attrs.resolver import FieldsBuilder
from gyver.attrs.utils.functions import frozen as freeze
from gyver.attrs.utils.functions import indent
from gyver.attrs.utils.typedef import MISSING, UNINITIALIZED, Descriptor, InitOptions

T = typing.TypeVar("T")

FieldMap = dict[str, Field]


@typing.overload
def define(
    maybe_cls: None = None,
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
) -> Callable[[type[T]], type[T]]:
    ...


@typing.overload
def define(
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = True,
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
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
    init: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    repr: bool = True,
    eq: bool = True,
    order: bool = True,
    hash: typing.Optional[bool] = None,
    pydantic: bool = False,
    dataclass_fields: bool = False,
    field_class: type[Field] = Field,
) -> typing.Union[Callable[[type[T]], type[T]], type[T]]:
    """
    Decorator function that adds functionality to a data class.

    :param maybe_cls: Optional[type[T]], a type argument that needs to be
    wrapped in the FieldsBuilder.
    :param frozen: bool, whether to create an immutable class or not.
    :param kw_only: bool, whether all params should be kw_only or not.
    :param slots: bool, whether to generate a class using __slots__ or not.
    :param repr: bool, whether to generate a __repr__ method or not.
    :param eq: bool, whether to generate an __eq__ method or not.
    :param order: bool, whether to generate rich comparison methods or not.
    :param hash: bool, whether to generate a __hash__ method or not.
    :param pydantic: bool, whether to generate a __get_validator__ method or
    not to facilitate integration with pydantic.
    :param dataclass_fields: bool, whether to add __dataclass_fields__ with the
    dataclass format. This way, the class becomes a drop-in replacement for dataclasses.
    **Warning**: dataclass_fields with pydantic=False will fail when trying to use with
    pydantic.

    :return: A callable object that wraps the maybe_cls type argument in a
    class that implements the specified features.
    :rtype: typing.Union[Callable[[type[T]], type[T]], type[T]]
    """

    def wrap(cls: type[T]) -> type[T]:
        fields = (
            FieldsBuilder(cls, kw_only, field_class, dataclass_fields)
            .from_annotations()
            .build()
        )
        field_map = {field.name: field for field in fields}
        clsdict = (
            _get_clsdict(cls, field_map)
            | _get_cls_metadata(cls)
            | _get_init(
                cls,
                field_map,
                {"frozen": frozen, "slots": slots, "init": init},
            )
            | _get_parse_dict(cls, field_map)
            | _get_gserialize(cls, field_map)
        )
        if slots:
            clsdict |= _get_slots_metadata(cls, field_map)
        if repr:
            clsdict |= _get_repr(cls, field_map)
        if eq:
            clsdict |= _get_eq(cls, field_map)
            clsdict |= _get_ne(cls)
        if order:
            clsdict |= _get_order(cls, field_map)
        if hash or (hash is None and frozen):
            clsdict |= _get_hash(cls, field_map, bool(hash))
        if pydantic:
            clsdict |= _get_pydantic_handlers(cls, field_map)
        if dataclass_fields:
            clsdict |= _make_dataclass_fields(field_map)
        maybe_freeze = freeze if frozen else lambda a: a
        return maybe_freeze(
            type(cls)(  # type: ignore
                cls.__name__,
                cls.__bases__,
                clsdict,
            )
        )

    return wrap(maybe_cls) if maybe_cls is not None else wrap


def _get_clsdict(cls: type, field_map: FieldMap):
    return {
        key: value
        for key, value in cls.__dict__.items()
        if key not in (tuple(field_map) + ("__dict__", "__weakref__"))
    } | {"__gyver_attrs__": field_map}


def _get_slots_metadata(
    cls: type,
    field_map: FieldMap,
) -> typing.Mapping[str, typing.Any]:
    inherited_slots: dict[str, typing.Any] = {}
    for base_cls in cls.mro()[1:-1]:
        inherited_slots |= {
            name: getattr(base_cls, name) for name in getattr(base_cls, "__slots__", ())
        }
    reused_slots = {
        slot: descriptor
        for slot, descriptor in inherited_slots.items()
        if slot in field_map
    }
    slot_names = tuple(field for field in field_map if field not in reused_slots)
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
            f"_setattr(self, '{field}', {arg})" if frozen else f"self.{field} = {arg}"
        )

    return _setattr


def _get_init(cls: type, field_map: FieldMap, opts: InitOptions):
    method_name = "__init__"
    if not opts["init"]:
        method_name = MethodBuilder.make_gattrs_name(method_name)
    builder = MethodBuilder(
        method_name,
        {
            "attr_dict": field_map,
            "MISSING": MISSING,
            "_setattr": object.__setattr__,
            "UNINITIALIZED": UNINITIALIZED,
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
        if not field.init:
            if field.has_default:
                builder.add_scriptline(
                    _setattr(field_name, f"attr_dict['{field_name}'].default")
                )
            elif field.has_default_factory:
                factory_name = f"__attr_factory_{field_name}"
                builder.add_scriptline(_setattr(field_name, f"{factory_name}()"))
                builder.add_glob(factory_name, field.default)
            else:
                builder.add_scriptline(_setattr(field_name, "UNINITIALIZED"))
            continue
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


def _get_repr(cls: type, field_map: FieldMap):
    fields = []
    globs = {}
    for field in field_map.values():
        if field.repr is False:
            continue
        elif field.repr is True:
            fields.append(f"{field.name}={{self.{field.name}!r}}")
        else:
            field_repr_call = f"__repr_{field.name}"
            globs[field_repr_call] = field.repr
            fields.append(f"{field.name}={{{field_repr_call}(self.{field.name})!r}}")
    fieldstr = ", ".join(fields)
    returnline = f"return f'{cls.__name__}({fieldstr})'"
    return (
        MethodBuilder("__repr__", globs)
        .add_annotation("return", str)
        .add_scriptline(returnline)
        .build(cls)
    )


_othername = "other"


def _get_eq(cls: type, field_map: FieldMap):
    fields_to_compare = {
        name: field for name, field in field_map.items() if field.eq is not False
    }
    builder = MethodBuilder("__eq__").add_funcarg(_othername)
    if fields_to_compare:
        return _build_field_comparison(builder, fields_to_compare, cls)
    returnline = "return _object_eq(self, other)"
    return (
        builder.add_glob("_object_eq", object.__eq__)
        .add_annotation("return", bool)
        .add_scriptline(returnline)
        .build(cls)
    )


def _build_field_comparison(
    builder: MethodBuilder, fields_to_compare: FieldMap, cls: type
):
    builder.add_scriptline("if type(other) is type(self):")
    args = []
    for field in fields_to_compare.values():
        arg = f"{{target}}.{field.name}"
        if field.eq is not True:
            glob_name = f"_parser_{field.name}"
            arg = f"{glob_name}({arg})"
            builder.add_glob(glob_name, field.eq)
        args.append(arg)

    fieldstr = "(" + ", ".join(args) + ",)"
    builder.add_scriptlines(
        indent(
            f"return {fieldstr.format(target='self')} "
            f"== {fieldstr.format(target=_othername)}",
        ),
        "else:",
        indent("return NotImplemented"),
    )
    return builder.add_annotation("return", bool).build(cls)


def _get_parse_dict(cls: type, field_map: FieldMap):
    namespace = {}
    args = []
    alias_args = []
    builder = (
        MethodBuilder(
            "__parse_dict__",
            {"deserialize": deserialize, "deserialize_mapping": deserialize_mapping},
        )
        .add_funcarg("alias")
        .add_annotation("alias", bool)
        .add_annotation("return", typing.Mapping[str, typing.Any])
    )
    for name, field in field_map.items():
        field_type = field.origin or field.declared_type
        if isinstance(field_type, str) and not field.asdict_:
            raise NotImplementedError(
                ("For now gyver-attrs cannot deal correctly" " with forward references")
            )
        builder.add_glob(f"field_type_{field.name}", field_type)
        if field.asdict_:
            builder.add_glob(f"_asdict_{field.name}", field.asdict_)
            arg = f"'{{name}}': _asdict_{field.name}(self.{name})"
        elif hasattr(field_type, "__parse_dict__"):
            arg = f"'{{name}}': self.{name}.__parse_dict__(alias)"
        elif not isinstance(field_type, type):
            arg = f"'{{name}}': self.{name}"
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
    namespace |= builder.build(cls)

    builder = MethodBuilder("__iter__", {"todict": deserialize})
    builder.add_scriptline("yield from todict(self).items()")
    return namespace | builder.build(cls)


def _get_parse_dict_sequence_arg(field: Field) -> str:
    field_type = field.origin or field.declared_type
    if not field.args:
        return f"'{{name}}': self.{field.name}"
    elif (
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


def _dict_get(mapping, name, alias, sentinel, dict_get):
    return (
        val
        if (val := dict_get(mapping, alias, sentinel)) is not sentinel
        else mapping[name]
    )


def _get_gserialize(cls: type, field_map: FieldMap):
    args = []
    builder = (
        MethodBuilder(
            "__gserialize__",
            {
                "dict_get": _dict_get,
                "sentinel": object(),
                "_dict_get": dict.get,
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
        get_line = (
            f"dict_get(mapping, {field.name!r}, {field.alias!r}," "sentinel, _dict_get)"
        )
        if field.fromdict:
            builder.add_glob(f"_field_type_{field.name}", field.fromdict)
            arg = f"_field_type_{field.name}({get_line})"
        elif hasattr(field_type, "__gserialize__"):
            arg = f"_field_type_{field.name}.__gserialize__({get_line})"
        elif field_type in (date, datetime):
            arg = f"_field_type_{field.name}.fromisoformat({get_line})"
        elif not isinstance(field_type, type):
            arg = f"({get_line})"
        elif issubclass(field_type, (list, tuple, set, dict)):
            arg, globs = _get_gserialize_sequence_arg(field)
            builder.merge_globs(globs)
        else:
            arg = f"_field_type_{field.name}({get_line})"
        args.append(f"{field.alias}={arg}")
    builder.add_scriptline(f"return cls({', '.join(args)})")
    return builder.build(cls)


def _get_gserialize_sequence_arg(
    field: Field,
) -> tuple[str, typing.Mapping[str, typing.Any]]:
    field_type = field.origin or field.declared_type
    globs = {}
    default_line = (
        f"dict_get(mapping, {field.name!r}, {field.alias!r}," "sentinel, _dict_get)"
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
                f"_field_type_{field.name}("
                f"_elem_type_{field.name}.__gserialize__(x)"
                f" for x in {default_line})"
            )
    return returnline, globs


def _get_ne(cls: type):
    return (
        MethodBuilder("__ne__")
        .add_funcarg(_othername)
        .add_annotation("return", bool)
        .add_scriptlines(
            "result = self.__eq__(other)",
            "if result is NotImplemented:",
            indent("return NotImplemented"),
            "else:",
            indent("return not result"),
        )
        .build(cls)
    )


def _get_order(cls: type, field_map: FieldMap):
    payload: dict[str, typing.Any] = {}

    for name, signal in [
        ("__lt__", "<"),
        ("__le__", "<="),
        ("__gt__", ">"),
        ("__ge__", ">="),
    ]:
        payload |= _make_comparator_builder(name, signal, field_map).build(cls)
    return payload


def _get_order_attr_tuple(fields: list[Field]) -> str:
    args = []
    for field in fields:
        arg = f"{{target}}.{field.name}"
        if field.order is not True:
            arg = f"_parser_{field.name}({arg})"
        args.append(arg)

    return f"({', '.join(args)},)"


def _make_comparator_builder(name: str, signal: str, field_map: FieldMap):
    fields = [
        field
        for field in field_map.values()
        if field.order is True or callable(field.order)
    ]
    if not fields:
        return (
            MethodBuilder(name, {f"_object_{name}": getattr(object, name)})
            .add_funcarg(_othername)
            .add_annotation("return", bool)
            .add_scriptline(f"return _object_{name}(self, other)")
        )
    builder = MethodBuilder(
        name,
        {f"_parser_{field.name}": field.order for field in field_map.values()},
    )
    attr_tuple = _get_order_attr_tuple(fields)
    return (
        builder.add_funcarg(_othername)
        .add_annotation("return", bool)
        .add_scriptlines(
            "if type(other) is type(self):",
            indent(
                "return "
                + f" {signal} ".join(
                    (
                        attr_tuple.format(target="self"),
                        attr_tuple.format(target="other"),
                    )
                ),
            ),
            "return NotImplemented",
        )
    )


def _get_hash(cls: type, fields_map: FieldMap, wants_hash: bool):
    builder = MethodBuilder("__hash__")
    args = ["type(self)"]
    for field in fields_map.values():
        if not field.hash:
            continue
        arg = f"self.{field.name}"
        field_type = field.origin or field.declared_type
        if field.hash is not True:
            glob = f"_hash_{field.name}"
            arg = f"{glob}({arg})"
            builder.add_glob(glob, field.hash)
        elif not isinstance(field.eq, bool):
            glob = f"_hash_{field.name}"
            arg = f"{glob}({arg})"
            builder.add_glob(glob, field.eq)
        elif not isinstance(field_type, type):
            pass  # Do not handle aliases and annotations
        elif not issubclass(field_type, typing.Hashable):
            if not wants_hash:
                continue
            raise TypeError("field type is not hashable", field.name, cls)
        args.append(arg)

    # if it only contains the class and no field qualifies for hashing
    if len(args) == 1:
        if not wants_hash:
            return {}
        raise TypeError("No hashable field found for class")

    return (
        builder.add_scriptline(f"return hash(({', '.join(args)}))")
        .add_annotation("return", int)
        .build(cls)
    )


def _get_pydantic_handlers(cls: type, fields_map: FieldMap):
    namespace = {}

    # Create Validation Function
    builder = MethodBuilder("__pydantic_validate__", {"fromdict": fromdict}).set_type(
        MethodType.CLASS
    )
    builder.add_funcarg("value").add_annotation("value", typing.Any).add_annotation(
        "return", cls
    )
    builder.add_scriptlines(
        "if isinstance(value, cls):",
        indent("return value"),
        "try:",
        indent("return fromdict(cls, dict(value))"),
        "except (TypeError, ValueError) as e:",
        indent(
            f"raise TypeError(f'{cls.__name__} expected dict not"
            " {type(value).__name__}')",
        ),
    )
    namespace |= builder.build(cls)

    # Write Get Validators
    builder = MethodBuilder("__get_validators__").set_type(MethodType.CLASS)

    builder.add_scriptline("yield cls.__pydantic_validate__ ")
    namespace |= builder.add_annotation(
        "return", typing.Generator[typing.Any, typing.Any, Callable]
    ).build(cls)

    # Make modify schema
    builder = (
        MethodBuilder("__modify_schema__")
        .set_type(MethodType.CLASS)
        .add_funcarg("field_schema")
    )

    cls_schema = schema.Schema(
        cls.__name__,
        "object",
        [f.argname for f in fields_map.values() if f.default is MISSING],
        properties=_generate_schema_lines(fields_map),
    )
    builder.add_scriptline(
        "field_schema.update({schema})".format(schema=cls_schema.to_string())
    )
    return namespace | builder.build(cls)


def _generate_schema_lines(fields_map: FieldMap) -> dict[str, schema.HasStr]:
    schemas: dict[str, schema.HasStr] = {}
    for field in fields_map.values():
        field_type = field.field_type
        if current_map := getattr(field_type, "__gyver_attrs__", None):
            required = [f.argname for f in current_map.values() if f.default is MISSING]
            schemas[field.argname] = schema.Schema(
                field_type.__name__,
                "object",
                required,
                properties=_generate_schema_lines(current_map),
            )
        else:
            schemas[field.argname] = _resolve_schematype(field.field_type, field.args)
    return schemas


def _resolve_schematype(
    field_type: type, args: typing.Sequence[type]
) -> schema.HasToString:
    _type_map = {
        type(None): "null",
        bool: "boolean",
        str: "string",
        float: "number",
        int: "integer",
    }
    if val := _type_map.get(field_type):
        return schema.DictSchema(val)
    if field_type in (list, set, tuple):
        extras = {}
        if args:
            extras["items"] = schema.Items(
                *(_resolve_schematype(arg, typing.get_args(arg)) for arg in args)
            )
        return schema.DictSchema("array", **extras)
    if field_type is dict:
        extras = {}
        if args:
            keyt, valt = args
            if keyt is not str:
                raise TypeError(
                    f"Cannot generate schema for dict with key type {keyt}",
                    keyt,
                )
            extras["additional_properties"] = _resolve_schematype(
                valt, typing.get_args(valt)
            )
        return schema.DictSchema("object", **extras)
    if current_map := getattr(field_type, "__gyver_attrs__", None):
        required = [f.argname for f in current_map.values() if f.default is MISSING]
        return schema.Schema(
            field_type.__name__,
            "object",
            required,
            properties=_generate_schema_lines(current_map),
        )
    if field_type is typing.Union:
        choices = [_resolve_schematype(arg, typing.get_args(arg)) for arg in args]
        return schema.ListSchema("anyOf", *choices)
    if issubclass(field_type, Enum):
        # remove from parents cls, enum.Enum and object
        # uses only the first of the mro
        parent, *_ = field_type.mro()[1:-2]
        if parent:
            if ft := _type_map.get(parent):
                type_name = ft
            else:
                raise NotImplementedError
        else:
            type_name = "string"
        return schema.Schema(
            field_type.__name__,
            type_name,
            enum=schema.Items(*[f'"{item.value}"' for item in field_type]),
        )
    if issubclass(field_type, datetime):
        return schema.DictSchema("string", format=schema.str_cast("date-time"))
    if issubclass(field_type, date):
        return schema.DictSchema("string", format=schema.str_cast("date"))
    if issubclass(field_type, time):
        return schema.DictSchema("string", format=schema.str_cast("time"))
    if issubclass(field_type, timedelta):
        return schema.DictSchema("number", format=schema.str_cast("time-delta"))
    raise NotImplementedError


def _make_dataclass_fields(fields_map: FieldMap):
    dc_fields = {}
    for field in fields_map.values():
        kwargs = {}
        if field.has_default:
            kwargs["default"] = field.default
        if field.has_default_factory:
            kwargs["default_factory"] = field.default
        if field.eq or field.order:
            kwargs["compare"] = True
        dc_field: dataclasses.Field = dataclasses.field(**kwargs)
        dc_field.name = field.name
        dc_field.type = field.declared_type
        dc_field._field_type = dataclasses._FIELD  # type: ignore
        dc_fields[field.name] = dc_field
    return {"__dataclass_fields__": dc_fields}
