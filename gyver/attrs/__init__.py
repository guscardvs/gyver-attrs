from .converters import asdict, asjson, fromdict, fromjson
from .field import info
from .main import define
from .camel import define_camel
from .helpers import fields, call_init
from .utils.factory import mark_factory
from .shortcuts import mutable, kw_only

__all__ = [
    "info",
    "define",
    "define_camel",
    "mark_factory",
    "asdict",
    "asjson",
    "fromdict",
    "fromjson",
    "fields",
    "call_init",
    "mutable",
    "kw_only",
]

__version__ = "0.3.0"
__version_info__ = tuple(map(int, __version__.split(".")))
