from .camel import define_camel
from .converters import asdict, asjson, fromdict, fromjson
from .field import info
from .helpers import call_init, fields, init_hooks
from .main import define
from .shortcuts import kw_only, mutable
from .utils.factory import mark_factory
from .utils.typedef import UNINITIALIZED

__all__ = [
    "info",
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
]

__version__ = "0.6.0"
__version_info__ = tuple(map(int, __version__.split(".")))
