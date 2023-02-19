from gattrs_converter import make_mapping, deserialize_mapping
from gyver.attrs import define
from gyver.attrs.field import info


@define
class B:
    z: int


@define
class A:
    x: int
    y: dict[int, B] = info(alias="yKey")


a = A(1, {item.z: item for item in [B(2), B(3), B(4)]})

print(deserialize_mapping(make_mapping(a)))
