import re
from collections.abc import Callable
from typing import Any, ForwardRef, TypeVar, Union, get_args, get_origin

from .typedef import UNINITIALIZED, DisassembledType, TypeNode

T = TypeVar('T')


def disassemble_type(typ: Union[type, str]) -> DisassembledType:
    type_ = typ if not isinstance(typ, str) else ForwardRef(typ)
    node = make_node(type_)
    _, type_vars = extract_typevar(node)
    return DisassembledType(type_, get_origin(type_), get_args(type_), type_vars, node)  # type: ignore


def make_node(type_: Union[type, ForwardRef]) -> TypeNode:
    root_node = TypeNode(get_origin(type_) or type_)
    stack = [(root_node, type_)]

    while stack:
        current_node, current_type = stack.pop()
        if get_origin(current_type) is None:
            continue

        type_args = get_args(current_type)
        for arg in type_args:
            if _arg := get_origin(arg):
                orig = _arg
            elif isinstance(arg, str):
                orig = ForwardRef(arg)
            else:
                orig = arg
            arg_node = TypeNode(orig)
            current_node.args.append(arg_node)
            stack.append((arg_node, arg))

    return root_node


def extract_typevar(
    node: TypeNode,
) -> tuple[TypeNode, tuple[tuple[TypeNode], ...]]:
    """Receives a type and returns a tuple with the original type and what typevars are part of it and at what depth"""
    if isinstance(node.type_, ForwardRef):
        return node, ()

    stack = [node]
    type_vars = []
    while stack:
        current = stack.pop()
        if isinstance(current.type_, TypeVar):
            type_vars.append(current)
        if current.args:
            for child in current.args:
                stack.append(child)

    return node, tuple(type_vars)


def get_forwardrefs(
    node: TypeNode,
) -> tuple[TypeNode, tuple[TypeNode, ...]]:
    stack = [node]
    type_vars = []
    depth = 0
    while stack:
        current = stack.pop()
        if isinstance(current.type_, ForwardRef):
            type_vars.append(current)
        if current.args:
            depth += 1
            for child in current.args:
                stack.append(child)

    return node, tuple(type_vars)


def rebuild_type(origin: type, args: tuple[Union[ForwardRef, type], ...]) -> type:
    if not hasattr(origin, '__getitem__'):
        raise TypeError('Unable to support rebuild, type has no __getitem__')
    try:
        return origin.__getitem__(*args)  # type: ignore
    except TypeError:
        return origin[args]  # type: ignore


def rebuild_type_from_depth(node: TypeNode) -> type:
    stack = [(node, None)]
    rebuilt_types = {}

    while stack:
        current_node, rebuilt_type = stack.pop()

        if isinstance(current_node.type_, ForwardRef) or not current_node.args:
            # If the current node is a ForwardRef, use it as the rebuilt type.
            # If the current node has no child nodes, it's a basic type.
            rebuilt_types[current_node] = current_node.type_
            rebuilt_types[current_node] = current_node.type_
        elif all(child in rebuilt_types for child in current_node.args):
            # If all child nodes have been rebuilt, reconstruct the type.
            arg_types = [rebuilt_types[child] for child in current_node.args]
            rebuilt_types[current_node] = rebuild_type(
                current_node.type_, tuple(arg_types)
            )
        else:
            # Push the current node back onto the stack and push its children.
            stack.append((current_node, rebuilt_type))
            for child in current_node.args:
                if child not in rebuilt_types:
                    stack.append((child, None))

    return rebuilt_types[node]


def frozen_setattr(self, name: str, value: Any):
    if getattr(self, name, UNINITIALIZED) is UNINITIALIZED:
        return object.__setattr__(self, name, value)
    del value
    raise AttributeError(
        f'Class {type(self)} is frozen, and attribute {name} cannot be set'
    )


def frozen_delattr(self, name: str):
    raise AttributeError(
        f'Class {type(self)} is frozen, and attribute {name} cannot be deleted'
    )


def frozen(cls: type[T]) -> type[T]:
    cls.__setattr__ = frozen_setattr
    cls.__delattr__ = frozen_delattr
    return cls


def indent(string: str, *, skip_line: bool = False) -> str:
    returnstr = f'    {string}'
    if skip_line:
        returnstr = '\n' + returnstr
    return returnstr


_sentinel = object()


def stamp_func(item: Union[Callable, classmethod, staticmethod]):
    to_stamp = item
    if isinstance(item, (classmethod, staticmethod)):
        to_stamp = item.__func__
    to_stamp.__gattrs_func__ = True


def implements(cls: type, name: str):
    attr = getattr(cls, name, _sentinel)
    if attr is _sentinel:
        return False

    if hasattr(attr, '__gattrs_func__'):
        return False

    if func := getattr(attr, '__func__', None):
        if hasattr(func, '__gattrs_func__'):
            return False
    return all(getattr(base_cls, name, None) is not attr for base_cls in cls.mro()[1:])


_to_camel_regex = re.compile('_([a-zA-Z])')


def to_camel(string: str) -> str:
    return _to_camel_regex.sub(lambda match: match[1].upper(), string.strip('_'))


def to_upper_camel(string: str) -> str:
    result = to_camel(string)
    return result[:1].upper() + result[1:]


_dunder_regex = re.compile('__[a-zA-Z0-9_]__')


def is_dunder(string: str) -> bool:
    return _dunder_regex.match(string) is not None


def sanitize(string: str) -> str:
    if is_dunder(string):
        return string
    return string.lstrip('_')
