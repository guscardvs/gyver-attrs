# Gyver Attrs
===========

Gyver Attrs is a lightweight library that simplifies the creation of Python data classes by providing a single decorator function, `define()`, that automatically adds useful class methods and attributes. With Gyver Attrs, you can easily create data classes that are immutable, hashable, comparable, and optimized for memory usage. Gyver Attrs will also support your descriptors that have private_names in slotted and frozen classes.

Features
--------
The `define()` function adds the following features to data classes:

* `__init__()` method for class initialization
* `__repr__()` method for string representation of the class instance
* `__eq__()` method for equality comparison of class instances
* `__ne__()` method for inequality comparison of class instances
* rich comparison methods (i.e., `__lt__()`, `__le__()`, `__gt__()`, `__ge__()`) for comparing class instances
* `__hash__()` method for hashable class instances
* `__slots__`attribute for reducing the memory footprint of class instances
* Fast converters to transform objects to and from dictionaries and JSON formats. These converters are implemented using a custom conversion library written in Rust and the ORJSON package. The conversion library is provided to offer high performance, making it suitable for large scale data operations.

To use the converters, the following functions are provided:

* **`asdict(obj)`**: Returns a dictionary containing the attributes of the input object.
* **`from_dict(type, dict)`**: Creates a new object of the specified type from the given dictionary.
* **`asjson(obj)`**: Returns a JSON string containing the attributes of the input object.
* **`from_json(type, obj)`**: Creates a new object of the specified type from the given JSON string.


Gyver Attrs uses the function `gyver.attrs.info` and the class `gyver.attrs.FieldInfo` in the same way as you would use `dataclass.field` or `pydantic.Field`. It accepts the following parameters:

* default: the default value for the field.
* alias: an alias name for the field.
* kw_only: whether the field is keyword-only.
* eq: whether the field should be included in the equality comparison method or a callable function for customizing equality comparison.
* order: whether the field should be included in the rich comparison methods or a callable function for customizing rich comparison.

The info() function returns a new instance of FieldInfo based on the parameters passed in. It accepts the same parameters as FieldInfo. FieldInfo provides additional methods like asdict() to get a dictionary representation of the field information, duplicate() to create a copy of the field with any overrides passed in, and build() to create a Field object based on the field information.

Usage
-----
The `define()` function can be used as a decorator on a data class definition or on an existing data class. It accepts the following keyword arguments:

* `frozen`: whether to create an immutable class or not (default is `True`)
* `kw_only`: whether to include keyword-only parameters in the constructor or not (default is `False`)
* `slots`: whether to generate a class using `__slots__` or not (default is `True`)
* `repr`: whether to generate a `__repr__` method or not (default is `True`)
* `eq`: whether to generate an `__eq__` method or not (default is `True`)
* `order`: whether to generate rich comparison methods or not (default is `True`)
* `hash`: whether to generate a `__hash__` method or not (default is `None`)

Usage Examples
--------
Here's an example of how to use the `define()` function:

```python
from gyver_attrs import define

@define
class MyClass:
    x: int
    y: int

@define(frozen=True, hash=True)
class Person:
    name: str
    age: int

p1 = Person(name="Alice", age=25)
p2 = Person(name="Bob", age=30)
p3 = Person(name="Alice", age=25)

assert p1 != p2
assert p1 == p3
assert hash(p1) == hash(p3)

@define
class Rectangle:
    width: float
    height: float

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        return 2 * (self.width + self.height)

r = Rectangle(width=10.0, height=5.0)

assert r.area() == 50.0
assert r.perimeter() == 30.0


@define(order=False)
class Point:
    x: int
    y: int

    def __add__(self, other: 'Point') -> 'Point':
        return Point(self.x + other.x, self.y + other.y)

    def __sub__(self, other: 'Point') -> 'Point':
        return Point(self.x - other.x, self.y - other.y)

p1 = Point(x=1, y=2)
p2 = Point(x=3, y=4)

assert p1 + p2 == Point(x=4, y=6)
assert p2 - p1 == Point(x=2, y=2)
```

Installation
--------
You can install gyver-attrs using pip
```console
pip install gyver-attrs
```

Contributing
--------
Contributions are welcome! Here are the steps to get started:
* Fork the repository and clone it locally.
* Install the required dependencies with **`poetry install --all-extras`**.
* Create a new branch for your changes with **`git checkout -b my-branch`**.
* Make your desired changes.
* Ensure that all tests pass with **`make test`**.
* Format the code with **`make format`**.
* Push your changes to your fork and create a pull request.

Thank you for contributing to gyver-attrs!