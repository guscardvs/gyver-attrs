from typing import Any, Mapping, cast
from gyver.attrs.field import Field

try:
    from gattrs_converter import make_mapping, deserialize_mapping, deserialize
except ImportError:

    def make_mapping(obj: Any, by_alias: bool = False) -> Mapping[str, Any]:
        if hasattr(obj, "__parse_dict__"):
            return obj.__parse_dict__()
        fields = cast(list[Field], getattr(obj, "__gyver_attrs__").values())
        return {
            field.alias if by_alias else field.name: getattr(obj, field.name)
            for field in fields
        }

    def deserialize_mapping(mapping: Mapping[str, Any]) -> Mapping[str, Any]:
        return {key: deserialize(value) for key, value in mapping.items()}

    def deserialize(value: Any):
        if hasattr(value, "__gyver_attrs__"):
            return deserialize(make_mapping(value))
        elif isinstance(value, Mapping):
            return deserialize_mapping(value)
        elif isinstance(value, (list, tuple, set)):
            return type(value)(map(deserialize, value))
        else:
            return value
