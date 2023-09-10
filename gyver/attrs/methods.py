import linecache
import sys
from enum import Enum
from typing import Any, Mapping, Optional, Union

from typing_extensions import Self

from gyver.attrs.utils.functions import implements, stamp_func

EllipsisType = type(...)


class MethodType(str, Enum):
    INSTANCE = "instance"
    CLASS = "class"
    STATIC = "static"


class MethodBuilder:
    def __init__(
        self, method_name: str, globs: Optional[dict[str, Any]] = None
    ) -> None:
        self.method_name = method_name
        self.globs = globs or {}
        self.script_lines: list[str] = []
        self.annotations: dict[str, Union[type, None]] = {}
        self.funcargs: list[str] = []
        self.funckargs: list[str] = []
        self.meth_type = MethodType.INSTANCE

    def add_scriptline(self, line: str) -> Self:
        self.script_lines.append(line)
        return self

    def add_scriptlines(self, *lines) -> Self:
        self.script_lines.extend(lines)
        return self

    def add_glob(self, name: str, value: Any) -> Self:
        self.globs[name] = value
        return self

    def merge_globs(self, globs: Mapping[str, Any]) -> Self:
        self.globs |= globs
        return self

    def add_annotation(self, name: str, value: Union[type, None]) -> Self:
        self.annotations[name] = value
        return self

    def add_funcarg(self, name: str) -> Self:
        self.funcargs.append(name)
        return self

    def add_funckarg(self, name: str) -> Self:
        self.funckargs.append(name)
        return self

    def set_type(self, meth_type: MethodType) -> Self:
        self.meth_type = meth_type
        return self

    def prepare_method_name(self, cls: type):
        method_name = self.method_name
        if implements(cls, method_name):
            method_name = self.make_gattrs_name(method_name)
        return method_name

    @staticmethod
    def make_gattrs_name(method_name: str) -> str:
        return "_".join(("__gattrs", method_name.lstrip("_")))

    def build(self, cls: type) -> dict[str, Any]:
        method_name = self.prepare_method_name(cls)
        method_annotations, method_script = self._make_methodstr(method_name)
        if cls.__module__ in sys.modules:
            self.merge_globs(sys.modules[cls.__module__].__dict__)
        func = _make_method(
            method_name,
            method_script,
            _generate_unique_filename(cls, method_name),
            self.globs,
        )
        func.__annotations__ = method_annotations
        stamp_func(func)
        return {method_name: func}

    def _make_methodstr(self, method_name: str):
        method_header = f"def {method_name}("
        method_footer = "):"
        method_decorator = ""

        if self.meth_type is MethodType.STATIC:
            method_decorator = "@staticmethod\n"
        elif self.meth_type is MethodType.CLASS:
            method_decorator = "@classmethod\n"
            self.funcargs.insert(0, "cls")
        else:
            self.funcargs.insert(0, "self")
        args = ", ".join(self.funcargs)
        if self.funckargs:
            args += f'{", " if args else ""}*, {", ".join(self.funckargs)}'
        method_signature = method_header + args + method_footer

        method_body = "\n    ".join(self.script_lines) if self.script_lines else "pass"
        if method_decorator:
            method_signature = method_decorator + method_signature

        method_annotations = {
            name: value
            for name, value in self.annotations.items()
            if value is not Ellipsis
        }
        method_script = f"{method_signature}\n    {method_body}"
        return method_annotations, method_script


def _make_method(
    name: str,
    script: str,
    filename: str,
    globs: dict[str, Any],
):
    """
    Create the method with the script given and return the method object.
    """
    locs: dict[str, Any] = {}

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
    globs: dict[str, Any],
    locs: Optional[Mapping[str, Any]] = None,
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
