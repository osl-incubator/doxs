"""tests/test_core.py - unit tests for YAML-powered *doxs*

The suite verifies that:
* The decorator (@doxs or @doxs(...)) injects *Parameters* / *Returns*.
* Generic type printing works (e.g. list[int]).
* `typing.Annotated` descriptions and defaults propagate.
* Class-level decoration adds *Attributes* and auto-decorates methods.
* The decorator is idempotent (no duplicate sections).
"""

from __future__ import annotations

from typing import Annotated

import doxs

from doxs import DocString


def _strip_indent(text: str) -> str:
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines)


def test_apply_on_function_generates_parameters_and_returns_sections():
    """Decorating a function should inject the expected docstring blocks."""

    @doxs(params={'x': 'The x value'}, returns='x squared')
    def square(x: int) -> int:
        return x * x

    doc = _strip_indent(square.__doc__ or '')

    assert 'Parameters' in doc
    assert 'Returns' in doc
    assert 'x : int' in doc
    assert 'The x value' in doc
    assert 'int' in doc
    assert 'x squared' in doc


def test_generic_type_rendering():
    """Type hints such as ``list[int]`` should be rendered nicely."""

    @doxs
    def give_first(values: list[int]) -> int:
        return values[0]

    doc = give_first.__doc__ or ''
    assert 'values : list[int]' in doc


def test_annotated_defaults_and_description():
    """`Annotated` wrapper should propagate description and default."""

    @doxs
    def add(
        x: Annotated[int, DocString('first term')] = 2,
        y: Annotated[int, 'second term'] = 3,
    ) -> Annotated[int, DocString('sum')]:
        return x + y

    doc = _strip_indent(add.__doc__ or '')
    assert 'first term' in doc
    assert 'default is `2`' in doc
    assert 'second term' in doc
    assert 'default is `3`' in doc
    assert 'sum' in doc


def test_apply_on_class_gen_attributes_section_and_auto_decorates_methods():
    """Class-level application should document attributes **and** methods."""

    @doxs(class_vars={'a': 'Alpha', 'b': 'Bravo'})
    class Demo:
        a: int = 1
        b: int = 2

        def add(self, value: int) -> int:
            """Arbitrary text that should be preserved."""
            return self.a + self.b + value

    cls_doc = _strip_indent(Demo.__doc__ or '')
    assert 'Attributes' in cls_doc
    assert 'a : int' in cls_doc and 'Alpha' in cls_doc
    assert 'b : int' in cls_doc and 'Bravo' in cls_doc

    meth_doc = _strip_indent(Demo.add.__doc__ or '')
    assert 'Parameters' in meth_doc
    assert 'value : int' in meth_doc
    assert 'Returns' in meth_doc


def test_idempotency_no_duplicate_sections():
    """Calling the decorator twice should not duplicate generated text."""

    @doxs
    def mul(x: int, y: int) -> int:
        return x * y

    first_doc = mul.__doc__ or ''
    doxs(mul)  # second application is a no-op
    second_doc = mul.__doc__ or ''

    assert first_doc == second_doc
    assert _strip_indent(first_doc).count('Parameters') == 1
