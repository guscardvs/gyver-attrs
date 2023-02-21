from typing import Any

from .utils import T, asdict, fromdict

try:
    import orjson

    json_loads = orjson.loads

    def json_dumps(v: Any, *, default=None):
        return orjson.dumps(v, default=default).decode()

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

    return json_dumps(asdict(obj, by_alias=by_alias))


def fromjson(
    into: type[T],
    json_str: str,
) -> T:
    val = json_loads(json_str)
    return fromdict(into, val)
