"""tests/example.py - YAML-powered showcase for *doxs*
=====================================================
Run this file to see how ``doxs`` reads YAML docstrings, injects the
numpydoc blocks, and preserves the original narrative sections.

    python -m tests.example
"""

from __future__ import annotations

from typing import Annotated, Any

import doxs


@doxs  # no explicit kwargs - YAML supplies everything
def add(x: int, y: int) -> int:
    """
    title: Return the sum of two integers
    summary: |
        This function returns the sum of two integer numbers.
    parameters:
        x: The first operand
        y: The second operand
    returns: Sum of *x* and *y*
    """
    return x + y


T = Any  # showcase that *any* type passes through


@doxs
def identity(value: T) -> T:
    """
    title: Identity function
    summary: Returns *value* unchanged.
    """


@doxs
class BasicCalculator:
    """
    title: Very small demo calculator
    attributes:
        a: First term
        b: Second term
    """

    a: int = 1
    b: int = 2

    def add(self) -> int:
        """
        title: Sum of internal operands
        returns: Sum of *self.a* and *self.b*
        """
        return self.a + self.b

    @doxs
    def multiply(self, scalar: int) -> int:
        """
        title: Multiply by *scalar*
        parameters:
            scalar: Number to multiply by
        returns: Scaled value
        """
        return (self.a + self.b) * scalar


@doxs
class FancyCalculator:
    """
    title: Showcase of ``Annotated`` inline usage
    """

    x: Annotated[float, doxs.DocString('First floating-point operand')] = 2.5
    y: Annotated[float, 'Second floating-point operand'] = 4.0

    def power(
        self,
        base: Annotated[float, doxs.DocString('Base')] = 2.0,
        exp: Annotated[float, 'Exponent'] = 3.0,
    ) -> Annotated[float, doxs.DocString('base ** exp')]:
        """
        title: Raise *base* to *exp*
        parameters:
            base: The base number
            exp: The exponent value
        returns: Result of ``base ** exp``
        """
        return base**exp


# ---------------------------------------------------------------------------
# 5.  Top-level constants (unrelated to *doxs* - just for completeness)
# ---------------------------------------------------------------------------

PI: float = 3.141592653589793
E: float = 2.718281828459045


# ---------------------------------------------------------------------------
# 6.  Mini demo when executed as a module
# ---------------------------------------------------------------------------


def _demo() -> None:
    print('Generated docstrings\n' + '=' * 80)

    for obj in (
        add,
        identity,
        BasicCalculator,
        BasicCalculator.add,
        BasicCalculator.multiply,
        FancyCalculator,
        FancyCalculator.power,
    ):
        print(f'\n>>> help({obj.__qualname__})')
        print('-' * 80)
        print(obj.__doc__)


if __name__ == '__main__':  # pragma: no cover
    _demo()
