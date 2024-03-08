from inspect import signature
from typing import Any, Generator, Sequence, TypeVar

from gyver.attrs import define, shortcuts
from gyver.attrs.utils.functions import disassemble_type


def _get_annotations_and_defaults(
    func,
) -> tuple[dict[str, type], dict[str, Any]]:
    hints = {}
    defaults = {}
    for item in signature(func).parameters.values():
        hints[item.name] = item.annotation
        defaults[item.name] = item.default
    return hints, defaults


def _args_equal(
    source: Sequence[type], target: Sequence[type]
) -> Generator[bool, None, None]:
    for source_arg, target_arg in zip(source, target):
        source_disassemble, target_disasseble = (
            disassemble_type(source_arg),
            disassemble_type(target_arg),
        )
        if source_disassemble.origin:
            assert source_disassemble.origin == target_disasseble.origin
            yield from _args_equal(source_disassemble.args, target_disasseble.args)
        elif isinstance(source_arg, TypeVar):
            yield source_arg.__name__ == target_arg.__name__
            yield source_arg.__bound__ == target_arg.__bound__  # type: ignore
        else:
            yield source_arg == target_arg


def test_shortcuts_are_up_to_date_with_define():
    define_hints, define_defaults = _get_annotations_and_defaults(define)

    annotation_generator = (
        (v[0], _get_annotations_and_defaults(v[1]))
        for v in (
            ('frozen', shortcuts.mutable),
            ('kw_only', shortcuts.kw_only),
            ('pydantic', shortcuts.schema_class),
        )
    )

    for without, (hints, defaults) in annotation_generator:
        for key, value in define_hints.items():
            if key == without:
                continue
            hint = disassemble_type(hints[key])
            define_hint = disassemble_type(value)

            assert hint.origin == define_hint.origin
            assert all(_args_equal(hint.args, define_hint.args))
            assert defaults[key] == define_defaults[key]
