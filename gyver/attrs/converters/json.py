from typing import Mapping, cast
from typing import Any

from .utils import make_mapping, unwrap_mapping


try:
    import orjson

    json_loads = orjson.loads

    def json_dumps(v: Any, *, default=None):
        return orjson.dumps(v, default == default).decode()

except ImportError:
    import json

    json_loads = json.loads

    def json_dumps(v: Any, *, default=None):
        return json.dumps(v, default=default)


def asjson(
    obj: Any,
    *,
    by_alias: bool = True,
) -> str:
    if not hasattr(obj, "__gyver_attrs__"):
        raise TypeError("Unable to parse classes not defined with `define`")
    mapping = unwrap_mapping(
        cast(Mapping[str, Any], getattr(obj, "__mapping__", make_mapping(obj)))
    )
