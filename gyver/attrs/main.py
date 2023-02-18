from collections.abc import Callable
import typing
import typing_extensions
import linecache

from gyver.attrs.field import Field, FieldInfo, info
from gyver.attrs.resolver import FieldsBuilder
from gyver.attrs.utils.functions import frozen as freeze
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
        )
        if slots:
            clsdict |= _get_slots_metadata(cls, field_map)
        if repr:
            clsdict |= _get_repr(cls, field_map)
        if eq:
            clsdict |= _get_eq(cls, field_map)
        maybe_freeze = freeze if frozen else lambda a: a

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
    if not opts["slots"]:
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


def _get_repr(cls: type, field_map: dict[str, Field]):
    fieldstr = ", ".join(
        f"{field.name}={{self.{field.name}!r}}" for field in field_map.values()
    )
    returnline = f"return f'{cls.__name__}({fieldstr})'"
    repr_script = f"def __repr__(self):\n    {returnline}"
    globs = {}
    repr_func = _make_method(
        "__repr__",
        repr_script,
        _generate_unique_filename(cls, "__repr__"),
        globs,
    )
    repr_func.__annotations__ = {"return": str}
    return {"__repr__": repr_func}


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
    eq_script = f"def __eq__(self, {othername}):\n    {returnline}"
    annotations = {"return": bool, "othername": cls}
    eq_func = _make_method(
        "__eq__", eq_script, _generate_unique_filename(cls, "__eq__"), {}
    )
    eq_func.__annotations__ = annotations
    return {"__eq__": eq_func}


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
