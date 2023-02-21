from datetime import datetime
from gyver.attrs import define
from gyver.attrs.converters.json import asjson, fromjson
from gyver.attrs.field import info


@define
class B:
    z: int


@define
class A:
    x: int
    y: tuple[B, B] = info(alias="yKey")
    w: datetime


@define
class C(A):
    pass


obj = A(1, (B(2), B(3)), datetime.now())
other = A(1, (B(2), B(3)), datetime.now())
target_json = asjson(obj)


def make_class():
    # for _ in range(100000):
    fromjson(A, target_json)


def with_other(meth):
    return lambda: meth(other)


# print(fromjson(A, target_json))
# print(timeit(make_class))
# print(cProfile.runctx("make_class()", globals(), locals()))
