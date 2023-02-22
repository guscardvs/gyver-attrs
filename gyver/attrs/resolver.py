from typing import Sequence, cast

from .field import Field, FieldInfo, default_info
from .utils.functions import disassemble_type
from .utils.typedef import MISSING


class FieldsBuilder:
    def __init__(self, cls: type, kw_only: bool):
        self.cls = cls
        self.kw_only = kw_only
        self.field_names: set[str] = set()
        self.parent_fields: list[Field] = []
        self.fields: list[Field] = []

    def build(self):
        self._add_parent_fields()
        fields = self.parent_fields + self.fields
        _validate_fields_order(fields)
        return tuple(fields)

    def _add_parent_fields(self):
        unfiltered_parent_fields = []
        for parent in reversed(self.cls.mro()[1:-1]):
            unfiltered_parent_fields.extend(
                field.inherit()
                for field in cast(
                    Sequence[Field],
                    getattr(parent, "__gyver_attrs__", {}).values(),
                )
                if field not in self.field_names and not field.inherited
            )
        seen = set()
        for field in reversed(unfiltered_parent_fields):
            if field.name in seen:
                continue
            self.parent_fields.insert(0, field)
            seen.add(field.name)
        self.field_names.update(seen)

    def add_field(self, key: str, annotation: type):
        default = getattr(self.cls, key, MISSING)
        info = default_info.duplicate(default=default)
        if isinstance(default, FieldInfo):
            info = default
        field = info.build(
            name=key,
            type_=disassemble_type(annotation),
            alias=info.alias or key,
        )
        self.fields.append(field)
        self.field_names.add(field.name)
        return self

    def from_annotations(self):
        if not hasattr(self.cls, "__annotations__"):
            return self
        for key, val in self.cls.__annotations__.items():
            self.add_field(key, val)
        return self


def _validate_fields_order(fields: list[Field]):
    had_default = False
    last_default_field = ""
    for field in fields:
        if field.kw_only:
            continue
        if had_default and field.default is MISSING:
            raise ValueError(
                f"Non default field {field.name!r}"
                " after field with default"
                f" {last_default_field!r} without kw_only flag"
            )
        if not had_default and field.default is not MISSING:
            last_default_field = field.name
            had_default = True
