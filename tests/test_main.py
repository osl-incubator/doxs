"""Tests for the core module."""

# Import the public surface of *doxs*.
try:
    from doxs.core import Annotation, apply  # type: ignore
except (
    ModuleNotFoundError
):  # pragma: no cover - allow running against a local clone
    import importlib
    import pathlib
    import sys

    ROOT = pathlib.Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(ROOT))
    apply = importlib.import_module('core').apply  # type: ignore
    Annotation = importlib.import_module('core').Annotation  # type: ignore


def _strip_indent(text: str) -> str:
    """Normalize indentation for reliable assertions."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    # Remove leading / trailing blank lines
    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()
    return '\n'.join(lines)


def test_apply_on_function_generates_parameters_and_returns_sections():
    """Decorating a function should inject the expected docstring blocks."""

    @apply(params={'x': 'The x value'}, returns='x squared')
    def square(x: int) -> int:
        return x * x

    doc = _strip_indent(square.__doc__ or '')

    assert 'Parameters:' in doc
    assert 'Returns:' in doc
    assert 'x : int' in doc
    assert 'The x value' in doc
    assert 'int' in doc
    assert 'x squared' in doc


def test_generic_type_rendering():
    """Type hints such as ``list[int]`` should be rendered nicely."""

    @apply
    def give_first(values: list[int]) -> int:
        return values[0]

    doc = give_first.__doc__ or ''
    assert 'values : list[int]' in doc


def test_annotation_defaults_and_description():
    """`Annotation` wrapper should propagate description and default."""

    @apply
    def add(
        x: Annotation(int, 'first term', default=2) = 2,
        y: Annotation(int, 'second term', default=3) = 3,
    ) -> Annotation(int, 'sum'):
        return x + y

    doc = _strip_indent(add.__doc__ or '')
    assert 'first term' in doc
    assert 'Default: 2' in doc
    assert 'second term' in doc
    assert 'Default: 3' in doc
    assert 'sum' in doc


def test_apply_on_class_gen_attributes_section_and_auto_decorates_methods():
    """Class-level application should document attributes **and** methods."""

    @apply(class_vars={'a': 'Alpha', 'b': 'Bravo'})
    class Demo:
        a: int = 1
        b: int = 2

        def add(self, value: int) -> int:
            """Arbitrary text that should be preserved."""
            return self.a + self.b + value

    # ---- Attribute section ----
    cls_doc = _strip_indent(Demo.__doc__ or '')
    assert 'Attributes:' in cls_doc
    assert 'a : int' in cls_doc and 'Alpha' in cls_doc
    assert 'b : int' in cls_doc and 'Bravo' in cls_doc

    # ---- Method section ----
    meth_doc = _strip_indent(Demo.add.__doc__ or '')
    assert 'Parameters:' in meth_doc
    assert 'value : int' in meth_doc
    assert 'Returns:' in meth_doc


def test_idempotency_no_duplicate_sections():
    """Calling ``apply`` twice should not duplicate generated text."""

    @apply
    def mul(x: int, y: int) -> int:
        return x * y

    first_doc = mul.__doc__ or ''
    # Second application should be a no-op
    apply(mul)
    second_doc = mul.__doc__ or ''

    assert first_doc == second_doc
    # Ensure only a single *Parameters* marker is present
    assert _strip_indent(first_doc).count('Parameters:') == 1
