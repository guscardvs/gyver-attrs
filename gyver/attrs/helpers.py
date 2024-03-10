import inspect
import sys
from collections.abc import Callable, Generator, Mapping, Sequence
from contextlib import contextmanager, suppress
from functools import wraps
from types import ModuleType
from typing import Any, ForwardRef, Literal, Optional, TypeVar, Union, cast, overload

from typing_extensions import Concatenate, ParamSpec

from .field import Field
from .main import _build_cls, _get_gserialize, _get_parse_dict
from .utils.functions import disassemble_type, get_forwardrefs, rebuild_type_from_depth

T = TypeVar('T')
R = TypeVar('R')
P = ParamSpec('P')


def validate_type(
    func: Callable[Concatenate[T, P], R],
) -> Callable[Concatenate[T, P], R]:
    @wraps(func)
    def inner(obj: T, *args: P.args, **kwargs: P.kwargs) -> R:
        if not hasattr(obj, '__gyver_attrs__'):
            raise TypeError(f'Type {obj} is not defined by gyver-attrs', obj)
        return func(obj, *args, **kwargs)

    return inner


@validate_type
def fields(cls: type) -> dict[str, Field]:
    """Returns the fields used to build the class
    by dict[name, Field]"""
    return cls.__gyver_attrs__


@validate_type
def call_init(self: Any, *args, **kwargs) -> None:
    """Calls __gattrs_init__ without having redlines in the code"""
    return gattrs_method('init', self, *args, **kwargs)


@overload
def gattrs_method(method_name: Literal['repr'], instance: Any) -> str: ...
@overload
def gattrs_method(
    method_name: Literal['eq', 'ne', 'lt', 'le', 'gt', 'ge'], instance: Any, other: Any
) -> bool: ...
@overload
def gattrs_method(
    method_name: Literal['parse_dict'], instance: Any, alias: bool
) -> Mapping[str, Any]: ...
@overload
def gattrs_method(
    method_name: Literal['gserialize'], instance: type[T], mapping: Mapping[str, Any]
) -> T: ...
@overload
def gattrs_method(method_name: Literal['hash'], instance: Any) -> int: ...
@overload
def gattrs_method(
    method_name: Literal['pydantic_validate'], instance: type[T], value: Any
) -> T: ...
@overload
def gattrs_method(
    method_name: Literal['get_validators'], instance: type
) -> Generator[Any, Any, Callable]: ...
@overload
def gattrs_method(
    method_name: Literal['modify_schema'], instance: type, field_schema
) -> None: ...
@overload
def gattrs_method(
    method_name: Literal['init'],
    instance: Any,
    *args,
    **kwargs,
) -> None: ...


def gattrs_method(method_name: str, instance: Any, *args, **kwargs) -> Any:
    _do_nothing(instance)
    method_name = method_name.strip('_')
    return (
        getattr(instance, f'__gattrs_{method_name}__', None)
        or getattr(instance, f'__{method_name}__')
    )(*args, **kwargs)


CallbackSequence = Sequence[Callable[[T], Any]]


def null_callable():
    pass


@contextmanager
@validate_type
def init_hooks(
    self: T,
    pre_callbacks: CallbackSequence[T] = (),
    post_callbacks: CallbackSequence[T] = (),
):
    pre_init = getattr(self, '__pre_init__', null_callable)
    post_init = getattr(self, '__post_init__', null_callable)

    for call in pre_callbacks:
        call(self)
    pre_init()
    yield
    for call in post_callbacks:
        call(self)
    post_init()


def update_refs(*, klasses: Sequence[type] = (), module: Optional[str] = None):
    """Updates ForwardRef fields for all klasses found in the module"""
    if klasses:
        return _update_refs(klasses)

    if not module:
        frame_info = next(
            (
                frame_info
                for frame_info in inspect.stack()[1:]
                if frame_info.filename != __file__
            ),
            None,
        )
        if not frame_info:
            return None
        module = frame_info.frame.f_globals['__name__']
    mod = sys.modules[module]  # type: ignore
    klasses = _extract_klass(mod)
    _update_refs(klasses)


def _update_refs(klasses: Sequence[type]):
    for k in klasses:
        update_ref(k)


@validate_type
def update_ref(cls: type):
    """Resolve ForwardRef fields from `cls`"""
    mod_globalns = sys.modules[cls.__module__].__dict__
    updated_fields = {}
    fields_map = fields(cls)
    for field in fields_map.values():
        _, frefs = get_forwardrefs(field.node)
        if not frefs:
            continue
        for forwardref in frefs:
            resolved = cast(ForwardRef, forwardref.type_)._evaluate(
                mod_globalns, mod_globalns, frozenset()
            )
            if not resolved:
                raise TypeError(
                    f'Unable to resolve ForwardRef for {cls.__qualname__}.{field.name}'
                )
            forwardref.type_ = resolved
        updated_fields[field.name] = field.duplicate(
            type_=disassemble_type(rebuild_type_from_depth(field.node))
        )
    if not updated_fields:
        return
    fields_map.update(updated_fields)
    parse_dict = _get_parse_dict(cls, fields_map)
    gserialize = _get_gserialize(cls, fields_map)
    for method_dict in (parse_dict, gserialize):
        (name, method), *_ = method_dict.items()
        type.__setattr__(cls, name, method)


@validate_type
def _do_nothing(val: Any):
    return val


def _extract_klass(mod: ModuleType):
    items = []
    for _, obj in inspect.getmembers(mod):
        with suppress(TypeError):
            items.append(_do_nothing(obj))
    return items


def resolve_typevars(*vars: tuple[TypeVar, Union[str, type]]):
    varsdict = dict(vars)

    @validate_type
    def resolver(cls: type):
        if not hasattr(cls, '__build_opts__'):
            raise TypeError(f'Unknown class {cls}')
        fields_map = fields(cls)
        updated_fields = {}
        for field in fields_map.values():
            if not field.has_type_vars:
                continue
            for typevar in field.type_.type_vars:
                if typevar.type_ in varsdict:
                    typevar.type_ = varsdict[typevar.type_]
            updated_fields[field.name] = field.duplicate(
                type_=disassemble_type(rebuild_type_from_depth(field.node))
            )
        fields_map.update(updated_fields)
        return _build_cls(cls.__source__, fields_map, **cls.__build_opts__)

    return resolver
