from gyver.attrs import define, info
from gyver.attrs.converters import json
from gyver.attrs.converters.json import asjson, fromjson
from gyver.attrs.converters.utils import asdict, fromdict


@define
class ExampleClass:
    x: int
    y: str = info(alias="y_alias")


def test_as_dict():
    mapping = {"x": 1, "y": "hello"}
    parsed = fromdict(ExampleClass, mapping)
    assert asdict(parsed, by_alias=False) == {"x": 1, "y": "hello"}

    mapping = {"x": 1, "y": [1, 2, 3]}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "[1, 2, 3]"}

    mapping = {"x": 1, "y": (1, 2, 3)}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "(1, 2, 3)"}

    mapping = {"x": 1, "y": {1, 2, 3}}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "{1, 2, 3}"}

    mapping = {"x": 1, "y": {"a": 1, "b": 2}}
    parsed = asdict(fromdict(ExampleClass, mapping))
    assert isinstance(parsed, dict)
    assert parsed == {"x": 1, "y": "{'a': 1, 'b': 2}"}


def test_unwrap_deeply_nested_mapping():
    """
    Test that unwrap properly unwraps a deeply nested mapping.
    """

    @define
    class D:
        d: str

    @define
    class C:
        c: tuple[D, ...]

    @define
    class B:
        b: C

    @define
    class A:
        a: B

    mapping = {"a": {"b": {"c": ({"d": "value"}, {"d": "another"})}}}

    unwrapped = asdict(A(B(C((D("value"), D("another"))))))

    assert unwrapped == mapping


def test_as_json():
    item = ExampleClass(1, "hello")
    assert asjson(item) == json.json_dumps({"x": 1, "y_alias": "hello"})
    assert asjson(item, by_alias=False) == json.json_dumps({"x": 1, "y": "hello"})


def test_nested_as_json():
    @define
    class Metadata:
        y: str = info(alias="meta")

    @define
    class B:
        x: int

    @define
    class A:
        a: B
        metadata: Metadata

    obj = A(B(1), Metadata("another"))

    assert asjson(obj) == json.json_dumps(
        {"a": {"x": 1}, "metadata": {"meta": "another"}}
    )

    assert asjson(obj, by_alias=False) == json.json_dumps(
        {"a": {"x": 1}, "metadata": {"y": "another"}}
    )


def test_fromjson():
    json_data = '{"x": 1, "y": "hello"}'
    assert fromjson(ExampleClass, json_data) == ExampleClass(1, "hello")

    @define
    class Metadata:
        y: str = info(alias="meta")

    @define
    class B:
        x: int

    @define
    class A:
        a: B
        metadata: Metadata

    obj = A(B(1), Metadata("another"))

    assert (
        fromjson(A, json.json_dumps({"a": {"x": 1}, "metadata": {"y": "another"}}))
        == obj
    )
