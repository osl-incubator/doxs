"""tests/test_core.py - unit tests for YAML-first *doxs*
Verify that:
* YAML docstrings are converted to numpydoc blocks.
* Generic type printing works (`list[int]`).
* `typing.Annotated` metadata propagates.
* Class-level decoration adds *Attributes* and auto-decorates methods.
* The decorator is idempotent.
"""

from __future__ import annotations

from typing import Annotated

import doxs
import pytest

from doxs import DocString


def _strip(text: str) -> str:
    """Normalize whitespace."""
    return '\n'.join(ln.rstrip() for ln in text.splitlines() if ln.rstrip())


def test_function_parameters_and_returns():
    """Decorator should inject Parameters / Returns blocks."""

    @doxs(params={'x': 'The x value'}, returns='x squared')
    def square(x: int) -> int:
        """
        title: square a value
        parameters:
            x: placeholder  # will be overridden
        returns: placeholder  # will be overridden
        """
        return x * x

    doc = _strip(square.__doc__ or '')
    assert 'Parameters' in doc and 'Returns' in doc
    assert 'x : int' in doc and 'The x value' in doc
    assert 'x squared' in doc


def test_generic_type_rendering():
    @doxs
    def give_first(values: list[int]) -> int:
        """title: generic list example"""
        return values[0]

    assert 'values : list[int]' in (give_first.__doc__ or '')


def test_annotated_descriptions_and_defaults():
    @doxs
    def add(
        x: Annotated[int, DocString('first term')] = 2,
        y: Annotated[int, 'second term'] = 3,
    ) -> Annotated[int, DocString('sum')]:
        """title: add two numbers"""
        return x + y

    doc = _strip(add.__doc__ or '')
    assert 'first term' in doc and 'default is `2`' in doc
    assert 'second term' in doc and 'default is `3`' in doc
    assert 'sum' in doc


def test_class_attributes_and_methods():
    @doxs(class_vars={'a': 'Alpha', 'b': 'Bravo'})
    class Demo:
        """title: demo class"""

        a: int = 1
        b: int = 2

        def add(self, value: int) -> int:
            """title: add internal attrs"""
            return self.a + self.b + value

    cls_doc = _strip(Demo.__doc__ or '')
    assert (
        'Attributes' in cls_doc and 'a : int' in cls_doc and 'Alpha' in cls_doc
    )
    assert 'b : int' in cls_doc and 'Bravo' in cls_doc

    meth_doc = _strip(Demo.add.__doc__ or '')
    assert (
        'Parameters' in meth_doc
        and 'value : int' in meth_doc
        and 'Returns' in meth_doc
    )


def test_idempotency():
    @doxs
    def mul(x: int, y: int) -> int:
        """title: multiply two ints"""
        return x * y

    first = mul.__doc__ or ''
    doxs(mul)
    second = mul.__doc__ or ''
    assert first == second and first.count('Parameters') == 1


def test_invalid_yaml_docstring_raises():
    """Check a docstring missing the required ``title`` key."""

    # YAML lacks the required 'title:' field
    with pytest.raises(ValueError):

        @doxs
        def bad(x: int) -> int:
            """
            parameters:
                x: just a number
            returns: the same number
            """
            return x
