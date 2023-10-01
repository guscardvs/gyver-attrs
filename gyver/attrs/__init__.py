from .camel import define_camel
from .converters import asdict, asjson, fromdict, fromjson
from .field import info, private
from .helpers import call_init, fields, init_hooks, update_ref, update_refs
from .main import define
from .shortcuts import kw_only, mutable
from .utils.factory import mark_factory
from .utils.typedef import UNINITIALIZED

__all__ = [
    "info",
    "private",
    "define",
    "define_camel",
    "mark_factory",
    "asdict",
    "asjson",
    "fromjson",
    "fromdict",
    "fields",
    "call_init",
    "init_hooks",
    "mutable",
    "kw_only",
    "UNINITIALIZED",
    "update_ref",
    "update_refs",
]

__version__ = "0.7.1"
__version_info__ = tuple(map(int, __version__.split(".")))
