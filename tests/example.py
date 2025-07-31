"""
Showcase of *doxs*.

A self-contained playground that demonstrates how to use the
:pyfunc:`doxs.apply` decorator and :pyclass:`doxs.Annotation` wrapper on
classes *and* functions.

Run this file directly to see the generated docstrings printed to the
console::

    python example.py
"""

from __future__ import annotations

from typing import Any

import doxs


@doxs.apply(
    params={'x': 'The first operand', 'y': 'The second operand'},
    returns='Sum of *x* and *y*',
)
def add(x: int, y: int) -> int:
    """Return the sum of two integers."""  # original docstring is preserved
    return x + y


T = Any


@doxs.apply  # no extra kwargs → decorator infers everything from annotations
def identity(value: T) -> T:
    """Return *value* unchanged."""


# ---------------------------------------------------------------------------
# 3.  A class using the decorator's *class_vars* helper
# ---------------------------------------------------------------------------


@doxs.apply(
    class_vars={'a': 'First term', 'b': 'Second term'},
)
class BasicCalculator:
    """Very small demo calculator."""

    a: int = 1
    b: int = 2

    def add(self) -> int:
        """Add ``self.a`` and ``self.b``."""
        return self.a + self.b

    @doxs.apply(
        params={'scalar': 'Number to multiply by'}, returns='Scaled value'
    )
    def multiply(self, scalar: int) -> int:
        """Multiply scalar."""
        return (self.a + self.b) * scalar


# ---------------------------------------------------------------------------
# 4.  A richer example using *Annotation* wrappers inline
# ---------------------------------------------------------------------------


@doxs.apply
class FancyCalculator:
    """Showcase of :pyclass:`doxs.Annotation` inline usage."""

    x: doxs.Annotation(float, 'First floating-point operand', default=2.5) = (
        2.5
    )
    y: doxs.Annotation(float, 'Second floating-point operand', default=4.0) = (
        4.0
    )

    def power(
        self,
        base: doxs.Annotation(float, 'Base', default=2.0) = 2.0,
        exp: doxs.Annotation(float, 'Exponent', default=3.0) = 3.0,
    ) -> doxs.Annotation(float, 'base ** exp'):
        """Raise **base** to **exp**."""
        return base**exp


# ---------------------------------------------------------------------------
# 5.  Top-level constants (with regular type hints - not strictly required)
# ---------------------------------------------------------------------------

PI: float = 3.141592653589793
E: float = 2.718281828459045


# ---------------------------------------------------------------------------
# 6.  Mini demo when run as a script
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    print('Generated docstrings\n' + '=' * 80)

    for obj in (
        add,
        identity,
        BasicCalculator,
        BasicCalculator.multiply,
        FancyCalculator,
        FancyCalculator.power,
    ):
        print(f'\n>>> help({obj.__qualname__})')
        print('-' * 80)
        print(obj.__doc__)
