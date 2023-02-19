from _gattrs_converter_utils import make_mapping, unwrap_mapping
from gyver.attrs import define, info


@define
class ExampleClass:
    x: int
    y: str = info(alias="y_alias")


def test_make_mapping():  # sourcery skip: extract-duplicate-method
    obj = ExampleClass(1, "hello")
    mapping = make_mapping(obj, by_alias=False)
    assert isinstance(mapping, dict)
    assert mapping == {"x": 1, "y": "hello"}

    mapping = make_mapping(obj, by_alias=True)
    assert isinstance(mapping, dict)
    assert mapping == {"x": 1, "y_alias": "hello"}


def test_unwrap_mapping():
    mapping = {"x": 1, "y": "hello"}
    py_dict = unwrap_mapping(mapping)
    assert isinstance(py_dict, dict)
    assert py_dict == {"x": 1, "y": "hello"}

    mapping = {"x": 1, "y": [1, 2, 3]}
    py_dict = unwrap_mapping(mapping)
    assert isinstance(py_dict, dict)
    assert py_dict == {"x": 1, "y": [1, 2, 3]}

    mapping = {"x": 1, "y": (1, 2, 3)}
    py_dict = unwrap_mapping(mapping)
    assert isinstance(py_dict, dict)
    assert py_dict == {"x": 1, "y": (1, 2, 3)}

    mapping = {"x": 1, "y": {1, 2, 3}}
    py_dict = unwrap_mapping(mapping)
    assert isinstance(py_dict, dict)
    assert py_dict == {"x": 1, "y": {1, 2, 3}}

    mapping = {"x": 1, "y": {"a": 1, "b": 2}}
    py_dict = unwrap_mapping(mapping)
    assert isinstance(py_dict, dict)
    assert py_dict == {"x": 1, "y": {"a": 1, "b": 2}}

    mapping = {"x": 1, "obj": ExampleClass(2, "world")}
    py_dict = unwrap_mapping(mapping)
    assert isinstance(py_dict, dict)
    assert py_dict == {"x": 1, "obj": {"x": 2, "y": "world"}}


def test_unwrap_deeply_nested_mapping():
    """
    Test that unwrap properly unwraps a deeply nested mapping.
    """

    @define
    class A:
        a: "B"

    @define
    class B:
        b: "C"

    @define
    class C:
        c: "tuple[D, ...]"

    @define
    class D:
        d: str

    mapping = {"a": {"b": {"c": ({"d": "value"}, {"d": "another"})}}}

    unwrapped = unwrap_mapping(
        make_mapping(A(B(C((D("value"), D("another"))))))
    )

    assert unwrapped == mapping
