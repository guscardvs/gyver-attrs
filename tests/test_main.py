import pathlib
import typing
from dataclasses import field
from unittest.mock import Mock

import pytest

from gyver.attrs import UNINITIALIZED, define, info, mark_factory
from gyver.attrs.helpers import call_init, init_hooks
from gyver.attrs.methods import MethodBuilder


@define
class Person:
    name: str
    age: int


def test_instantiation_runs_without_errors():
    Person("John Doe", 46)


def test_no_slots_class_is_also_valid():
    @define(slots=False)
    class NoSlots:
        x: int

    ns = NoSlots(1)

    assert {"x": 1} == getattr(ns, "__dict__")


def test_frozen_works_correctly():
    person = Person("John Doe", 46)

    with pytest.raises(AttributeError):
        person.name = "Jane Doe"


def test_frozen_can_be_disabled():
    @define(frozen=False)
    class NotFrozen:
        x: int

    nf = NotFrozen(1)

    nf.x = 2

    assert nf.x == 2


def test_repr_returns_the_expected_string():
    @define
    class Another:
        email: str
        name: str = info(repr=str.title)
        password: str = info(repr=False)

    person = Person("Jane Doe", 30)
    another = Another("test@example.com", "valerica", "Very Important Secret")

    assert repr(person) == "Person(name='Jane Doe', age=30)"
    assert repr(another) == "Another(email='test@example.com', name='Valerica')"


def test_defaults_work_as_expected():
    @define
    class WithDefault:
        x: int = 4

    wd = WithDefault()

    assert wd.x == 4


def test_defaults_work_with_factory():
    def make_factory():
        val = 0

        def fac() -> int:
            nonlocal val
            val += 1
            return val

        return fac

    @define
    class WithFactory:
        x: int = info(default=mark_factory(make_factory()))

    wf = WithFactory()
    wf2 = WithFactory()

    assert wf.x == 1
    assert wf2.x == 2


def test_exceptions_are_detected_and_handled():
    @define
    class E(Exception):
        msg: str
        other: int

    with pytest.raises(E) as ei:
        raise E("yolo", 42)

    e = ei.value

    assert ("yolo", 42) == e.args
    assert "yolo" == e.msg
    assert 42 == e.other


def test_mro_uses_the_rightmost_parent_attribute():
    @define
    class A:
        x: int = 10

        def xx(self):
            return 10

    @define
    class B(A):
        y: int = 20

    @define
    class C(A):
        x: int = 50

        def xx(self):
            return 50

    @define
    class D(B, C):
        pass

    d = D()

    assert d.x == d.xx()
    assert d.y == 20


def test_eq_validates_equality_correctly():
    @define
    class A:
        x: int

    a = A(1)
    a2 = A(1)
    assert a == a2


def test_eq_validates_inequality_correctly():  # sourcery skip: de-morgan
    @define(frozen=False, slots=False)
    class A:
        x: int

    eq_mock = Mock()
    eq_mock.return_value = True

    a = A(1)
    a.__eq__ = eq_mock
    a2 = A(1)

    assert not (a != a2)
    assert eq_mock.call_count == 1


def test_info_allows_opt_out_of_equality():
    @define
    class A:
        x: int
        y: int
        z: int = info(eq=False)

    assert A(1, 2, 3) == A(1, 2, 4)
    assert A(1, 2, 3) != A(1, 3, 3) != A(2, 2, 3)


def test_attrs_allow_addition_of_descriptors_on_slotted_classes():
    class AccessCounter:
        def __init__(self, func) -> None:
            self.func = func

        def __set_name__(self, owner: type, name: str):
            self.public_name = name
            self.private_name = f"_access_counter_{name}"

        def __get__(self, instance, owner):
            if not instance:
                return self
            value = getattr(instance, self.private_name, 0)
            result = self.func(instance)
            object.__setattr__(instance, self.private_name, value + 1)
            return result, value

    @define
    class MyCls:
        @AccessCounter
        def a(self):
            return "Hello"

    instance = MyCls()

    assert MyCls.a.private_name in MyCls.__slots__
    assert instance.a == ("Hello", 0)
    assert instance.a == ("Hello", 1)
    assert instance.a == ("Hello", 2)


def test_alias_support_works_correctly():
    @define
    class A:
        x: int = info(alias="xVal")

    a = A(xVal=2)

    assert a.x == 2


def test_post_and_pre_init_work_correctly():
    val = 0

    @define
    class A:
        def __pre_init__(self):
            nonlocal val
            val += 1

        def __post_init__(self):
            nonlocal val
            val += 1

    A()

    assert val == 2


def test_define_compares_correctly_with_parser():
    @define
    class Person:
        name: str = info(eq=str.lower)

    @define
    class A:
        x: int = info(eq=lambda val: val % 3)

    assert Person("John") == Person("john") != Person("jane")
    assert A(3) == A(6) != A(7)


def test_define_creates_ordering_correctly():
    @define
    class A:
        x: int
        y: int
        z: int

    @define(order=False)
    class Unorderable:
        x: int

    a1 = A(1, 2, 3)
    a2 = A(2, 3, 4)
    a3 = A(2, 4, 5)

    items = [a3, a1, a2]
    expected = [a1, a2, a3]

    for item in sorted(items):
        assert item is expected.pop(0)

    for item in ["__lt__", "__gt__", "__le__", "__ge__"]:
        assert hasattr(A, item)

    with pytest.raises(TypeError):
        Unorderable(1) > Unorderable(2)  # type: ignore


def test_define_creates_ordering_only_for_direct_instances():
    @define
    class A:
        x: int

    class B(A):
        pass

    with pytest.raises(TypeError):
        A(1) < B(1)  # type: ignore


def test_define_creates_hashable_classes():
    @define
    class A:
        x: int

    @define
    class B:
        x: int = info(eq=lambda val: val % 3)

    @define
    class C:
        x: int = info(hash=lambda val: val * 3)
        y: int = info(hash=False)

    @define
    class D:
        x: int = info(hash=lambda val: val / 3, eq=lambda val: val * 3)

    sentinel = object()

    assert isinstance(A(1), typing.Hashable)
    assert {A(1): sentinel}[A(1)] is sentinel
    assert hash(A(2)) != hash(A(1)) == hash(A(1))
    assert hash(B(3)) == hash(B(6)) != hash(B(7))
    assert A(1) is not A(2)
    assert hash(C(3, 2)) == hash(C(3, 1))
    assert hash(D(3)) == hash((D, 3 / 3))


def test_define_does_not_create_hashable_when_it_shouldnt():
    @define(hash=False)
    class A:
        x: int

    @define(frozen=False)
    class B:
        x: int

    with pytest.raises(TypeError):
        hash(A(1))
    with pytest.raises(TypeError):
        hash(B(1))

    class C:
        x: list[int]

    with pytest.raises(TypeError) as exc_info:
        define(hash=True)(C)

    assert exc_info.value.args == ("field type is not hashable", "x", C)
    assert not issubclass(
        define(C), typing.Hashable
    ), "should not complain if class does not want explicitly hash"


def test_define_does_not_overwrite_methods_but_creates_gattrs_alternatives():
    @define
    class A:
        z: int = False

    @define
    class B:
        a: int
        b: int

        def __init__(self, a: int, b: int):
            self.__gattrs_init__(a, b)

        def __repr__(self):
            return f"B(a={self.a}, b={self.b})"

        def __eq__(self, other):
            if other.__class__ is self.__class__:
                return (self.a, self.b) == (other.a, other.b)
            else:
                return NotImplemented

        def __ne__(self, other):
            result = self.__eq__(other)

            return NotImplemented if result is NotImplemented else not result

        def __lt__(self, other):
            if other.__class__ is self.__class__:
                return (self.a, self.b) < (other.a, other.b)
            else:
                return NotImplemented

        def __le__(self, other):
            if other.__class__ is self.__class__:
                return (self.a, self.b) <= (other.a, other.b)
            else:
                return NotImplemented

        def __gt__(self, other):
            if other.__class__ is self.__class__:
                return (self.a, self.b) > (other.a, other.b)
            else:
                return NotImplemented

        def __ge__(self, other):
            if other.__class__ is self.__class__:
                return (self.a, self.b) >= (other.a, other.b)
            else:
                return NotImplemented

        def __hash__(self):
            return hash((self.__class__, self.a, self.b))

    methods = [
        "__init__",
        "__repr__",
        "__eq__",
        "__hash__",
        "__ne__",
        "__lt__",
        "__le__",
        "__gt__",
        "__ge__",
    ]

    for method in methods:
        gattr_method = "_".join(("__gattrs", method.lstrip("_")))
        assert hasattr(A, method) and not hasattr(A, gattr_method)
        assert hasattr(B, gattr_method)


Validator = typing.Callable[[typing.Any], bool]


def test_defines_correctly_classes_with_non_types_as_hints():
    @define
    class Whatever:
        validator: Validator
        root: pathlib.Path
        look_on: typing.Optional[pathlib.Path] = None
        exclude: typing.Sequence[typing.Union[str, pathlib.Path]] = ()


def test_init_false_does_sets_values_with_proper_initial_values():
    @define
    class Whatever:
        name: str
        email: str = info(init=False)
        age: int = info(init=False, default=18)
        friend: list[str] = info(init=False, default_factory=list)

    whatever = Whatever("hello")

    assert whatever.email is UNINITIALIZED
    assert whatever.age == 18
    assert whatever.friend == []

    assert "email" not in typing.get_type_hints(Whatever.__init__)

    whatever.email = "world"
    assert whatever.email == "world"

    with pytest.raises(AttributeError):
        whatever.email = "Hello"


def test_define_init_does_not_add_init_function():
    @define(init=False, frozen=False)
    class Whatever:
        name: str

    assert Whatever.__init__ is object.__init__
    assert hasattr(Whatever, MethodBuilder.make_gattrs_name("__init__"))

    whatever = Whatever()
    call_init(whatever, name="Hello")

    assert whatever.name == "Hello"


def test_init_hooks():
    @define(init=False, frozen=False)
    class TestObject:
        pre_init_called: bool = info(init=False)
        post_init_called: bool = info(init=False)

        def __pre_init__(self):
            self.pre_init_called = True

        def __post_init__(self):
            self.post_init_called = True

    pre_callback_called = False
    post_callback_called = False

    def pre_callback(obj):
        nonlocal pre_callback_called
        pre_callback_called = True

    def post_callback(obj):
        nonlocal post_callback_called
        post_callback_called = True

    obj = TestObject()

    with init_hooks(
        obj,
        pre_callbacks=[pre_callback],
        post_callbacks=[post_callback],
    ):
        assert hasattr(obj, "pre_init_called")  # pre-init should be called
        assert not hasattr(obj, "post_init_called")  # post-init should not be called
        assert pre_callback_called is True  # Pre-callback should be called
        assert post_callback_called is False  # Post-callback should not be called

    assert hasattr(
        obj, "post_init_called"
    )  # post-init should be called after the context

    pre_callback_called = False
    post_callback_called = False

    del obj.post_init_called, obj.pre_init_called

    with init_hooks(obj):
        assert hasattr(obj, "pre_init_called")  # pre-init should be called
        assert not hasattr(obj, "post_init_called")  # post-init should not be called

    assert hasattr(
        obj, "post_init_called"
    )  # post-init should be called after the context


def test_init_hooks_ignores_hooks_if_hooks_dont_exist():
    @define
    class Test:
        pass

    obj = Test()

    with init_hooks(obj):
        pass  # no exceptions should be raised


def test_define_is_drop_in_replacement_for_dataclass():
    @define(frozen=False, dataclass_fields=True)
    class Test:
        order_field: int
        name: str = field(init=False)
        email: str = field(hash=False)
        age: int = field(compare=False)
        password: str = field(default="MyPassword")
        friends: list[str] = field(default_factory=list)

    default_obj = Test(1, email="Hello", age=18)
    another = Test(0, email="World", age=19)

    assert default_obj.name is UNINITIALIZED
    assert default_obj.email == "Hello"
    assert default_obj.password == "MyPassword"
    assert default_obj.friends == []

    assert sorted([default_obj, another]) == [another, default_obj]
