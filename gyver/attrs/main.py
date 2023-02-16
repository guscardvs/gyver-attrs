from collections.abc import Callable
import typing
import typing_extensions
import linecache

from gyver.attrs.field import Field, FieldInfo, info
from gyver.attrs.utils.functions import disassemble_type, frozen as freeze
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
) -> Callable[[type[T]], type[T]]:
    ...


@typing.overload
def define(
    maybe_cls: type[T],
    /,
    *,
    frozen: bool = True,
    slots: bool = True,
) -> type[T]:
    ...


@typing_extensions.dataclass_transform(
    order_default=True,
    frozen_default=True,
    kw_only_default=False,
    field_specifiers=((FieldInfo, info)),
)
def define(
    maybe_cls: typing.Optional[type[T]] = None,
    /,
    *,
    frozen: bool = True,
    kw_only: bool = False,
    slots: bool = True,
    extra_descriptors: typing.Sequence[type[Descriptor]] = (),
) -> typing.Union[Callable[[type[T]], type[T]], type[T]]:
    def wrap(cls: type[T]) -> type[T]:
        fields = _map_fields(cls, kw_only)
        field_map = {field.name: field for field in fields}
        clsdict = (
            _get_clsdict(cls, field_map)
            | _get_cls_metadata(cls)
            | _get_init(cls, field_map, {"frozen": frozen, "slots": slots})
        )
        if slots:
            clsdict |= _get_slots_metadata(cls, field_map, extra_descriptors)

        maybe_freeze = freeze if frozen else lambda a: a

        return maybe_freeze(type(cls)(cls.__name__, cls.__bases__, clsdict))

    return wrap(maybe_cls) if maybe_cls is not None else wrap


def _map_fields(cls: type, kw_only: bool) -> Fields:
    fields: list[Field] = []
    for key, annotation in cls.__annotations__.items():
        info = getattr(cls, key, MISSING)
        default = info
        alias = ""
        if isinstance(info, FieldInfo):
            default = info.default
            alias = info.alias
            kw_only = kw_only or info.kw_only
        fields.append(
            Field(
                key,
                disassemble_type(annotation),
                kw_only,
                default,
                alias or key,
            )
        )
    field_names = {item.name for item in fields}
    parent_fields: list[Field] = []
    for parent in reversed(cls.mro()[1:-1]):
        parent_fields.extend(
            field
            for field in getattr(parent, "__gyver_attrs__", {}).values()
            if field not in field_names
        )

    seen = set()
    parent_result = []
    # will use the leftmost child
    # when getting inherited definitions
    for field in reversed(parent_fields):
        if field.name in seen:
            continue
        parent_result.insert(0, field)
        seen.add(field.name)

    fields = parent_result + fields
    had_default = False
    last_default_field = ""
    for field in fields:
        if field.kw_only:
            continue
        if had_default and field.default is MISSING:
            raise ValueError(
                f"Non default field {field.name!r} after field with default"
                f" {last_default_field!r} without kw_only flag"
            )
        if not had_default and field.default is not MISSING:
            last_default_field = field.name
            had_default = True

    return tuple(fields)


def _get_clsdict(cls: type, field_map: dict[str, Field]):
    return {
        key: value
        for key, value in cls.__dict__.items()
        if key not in (tuple(field_map) + ("__dict__", "__weakref__"))
    } | {"__gyver_attrs__": field_map}


def _get_slots_metadata(
    cls: type,
    field_map: dict[str, Field],
    extra_descriptors: typing.Sequence[Descriptor],
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
        if _is_descriptor_type(value) and type(value) in extra_descriptors:
            slot_names += (value.private_name,)
    return inherited_slots | reused_slots | {"__slots__": tuple(slot_names)}


def _is_descriptor_type(
    obj: typing.Any,
) -> typing_extensions.TypeGuard[Descriptor]:
    return hasattr(obj, "private_name")


def _get_cls_metadata(cls: type):
    return {"__qualname__": cls.__qualname__}


def _make_setattr(slots: bool):
    def _setattr(field: str, arg: typing.Any):
        return (
            f"_setattr(self, '{field}', {arg})"
            if slots
            else f"_inst_dict['{field}'] = {arg}"
        )

    return _setattr


def _get_init(cls: type, field_map: dict[str, Field], opts: InitOptions):
    script_lines = []
    _setattr = _make_setattr(opts["slots"])
    if not opts["frozen"]:
        script_lines.append("_inst_dict = self.__dict__")
    args = []
    kw_only_args = []

    globs = {
        "attr_dict": field_map,
        "MISSING": MISSING,
        "_setattr": object.__setattr__,
    }
    annotations: dict[str, typing.Any] = {"return": None}

    for field in field_map.values():
        field_name = field.name
        arg_name = field.alias.lstrip("_")
        if field.has_default:
            arg = f"{arg_name}=attr_dict['{field_name}'].default"

            script_lines.append(_setattr(field_name, arg_name))
        elif field.has_default_factory:
            arg = f"{arg_name}=MISSING"

            init_factory_name = f"__attr_factory_{field_name}"
            script_lines.extend(
                (
                    f"if {arg_name} is not MISSING:",
                    f"    {_setattr(field_name, arg_name)}",
                    "else:",
                    f'    {_setattr(field_name, f"{init_factory_name}()")}',
                )
            )
            globs[init_factory_name] = field.default
        else:
            script_lines.append(_setattr(field_name, arg_name))
            arg = arg_name
        if field.kw_only:
            kw_only_args.append(arg)
        else:
            args.append(arg)
        annotations[arg_name] = field.declared_type
    args = ", ".join(args)
    if kw_only_args:
        args += f'{", " if args else ""}*, {", ".join(kw_only_args)}'
    script_lines_payload = (
        "\n    ".join(script_lines) if script_lines else "pass"
    )
    init_script = f"def __init__(self, {args}):\n    {script_lines_payload}"
    init = _make_method(
        "__init__",
        init_script,
        _generate_unique_filename(cls, "__init__"),
        globs,
    )
    init.__annotations__ = annotations
    return {"__init__": init}


def _make_method(
    name: str,
    script: str,
    filename: str,
    globs: dict[str, typing.Any],
):
    """
    Create the method with the script given and return the method object.
    """
    locs = {}

    count = 1
    base_filename = filename
    while True:
        linecache_tuple = (
            len(script),
            None,
            script.splitlines(True),
            filename,
        )
        old_val = linecache.cache.setdefault(filename, linecache_tuple)
        if old_val == linecache_tuple:
            break
        filename = f"{base_filename[:-1]}-{count}>"
        count += 1

    _compile_and_eval(script, globs, locs, filename)

    return locs[name]


def _compile_and_eval(
    script: str,
    globs: dict[str, typing.Any],
    locs: typing.Optional[typing.Mapping[str, typing.Any]] = None,
    filename: str = "",
) -> None:
    """
    "Exec" the script with the given global (globs) and local (locs) variables.
    """
    bytecode = compile(script, filename, "exec")
    eval(bytecode, globs, locs)


def _generate_unique_filename(cls, func_name):
    """
    Create a "filename" suitable for a function being generated.
    """
    return (
        f"<gyver {func_name} {cls.__module__}."
        f"{getattr(cls, '__qualname__', cls.__name__)}>"
    )
