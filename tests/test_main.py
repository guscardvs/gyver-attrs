from gyver.attrs import define, info, mark_factory
import pytest


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

    person = Person("Jane Doe", 30)
    another = Another("test@example.com")

    assert repr(person) == "Person(name='Jane Doe', age=30)"
    assert repr(another) == "Another(email='test@example.com')"


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


def test_eq_validates_equality_correctly():
    @define
    class A:
        x: int

    a = A(1)
    a2 = A(1)

    assert a == a2


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
