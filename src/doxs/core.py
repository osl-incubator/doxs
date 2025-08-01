'''
Doxs core library - YAML-first flavour.

Turns YAML-formatted docstrings into enriched *numpydoc* sections.

Example
-------
```python
@doxs  # or simply ``@doxs`` if you re-export apply at top level
def add(x: int, y: int) -> int:
    """
    title: Return the sum of two integers
    summary: |
        This function returns the sum of two integer numbers.
    parameters:  # noqa
        x: The first operand
        y: The second operand
    returns: Sum of *x* and *y*
    """
    return x + y
```

The decorator will append a numpydoc block like:

```

Parameters
----------
x : int, default is `…`
    The first operand
...
```
'''

from __future__ import annotations

import inspect
import textwrap

from dataclasses import dataclass
from typing import (
    Annotated,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

import yaml

from typing_extensions import ParamSpec
from typing_extensions import get_type_hints as get_type_hints_ext

__all__ = ['DocString', 'apply']
_SENTINEL = '__doxs_applied__'

T = TypeVar('T', bound=type)
P = ParamSpec('P')
R = TypeVar('R')


# ---------------------------------------------------------------------------
# Helper: metadata wrapper for Annotated
# ---------------------------------------------------------------------------


@dataclass
class DocString:
    """Carry a description inside ``typing.Annotated`` metadata."""

    description: str


# ---------------------------------------------------------------------------
# YAML utils
# ---------------------------------------------------------------------------


def _parse_yaml(raw: str) -> Dict[str, Any]:
    """Parse *raw* as YAML or raise ``ValueError``."""

    if not raw or ':' not in raw:
        raise ValueError("Docstring is not valid YAML: missing ':'")
    try:
        data = yaml.safe_load(textwrap.dedent(raw))
    except yaml.YAMLError as exc:  # pragma: no cover
        raise ValueError(f'Docstring is not valid YAML: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('YAML root must be a mapping')
    return data


def _narrative(yaml_dict: Dict[str, Any]) -> str:
    title = str(yaml_dict.get('title', '')).strip()
    summary = str(yaml_dict.get('summary', '')).rstrip()
    parts: List[str] = []
    if title:
        parts.append(title if title.endswith('.') else title + '.')
    if summary:
        parts.append(summary)
    return '\n\n'.join(parts).strip()


# ---------------------------------------------------------------------------
# Decorator entry point
# ---------------------------------------------------------------------------


def apply(
    _obj: Any = None,
    *,
    class_vars: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    returns: Optional[Union[str, List[str]]] = None,
) -> Any:
    """Decorate a class or callable and convert YAML → numpydoc."""

    def decorator(obj: Any) -> Any:
        if inspect.isclass(obj):
            return _decorate_class(obj, class_vars or {})
        if callable(obj):
            return _decorate_func(obj, params or {}, returns)
        return obj

    return decorator if _obj is None else decorator(_obj)


# ---------------------------------------------------------------------------
# Class decoration
# ---------------------------------------------------------------------------


def _decorate_class(cls: T, overrides: Dict[str, str]) -> T:
    if getattr(cls, _SENTINEL, False):
        return cls

    yaml_dict = _parse_yaml(inspect.getdoc(cls) or '')
    narrative = _narrative(yaml_dict)

    # Build Attributes block
    attr_lines: List[str] = []
    try:
        annotations = get_type_hints(cls, include_extras=True)
    except TypeError:
        annotations = get_type_hints_ext(cls, include_extras=True)

    for name, annotation in annotations.items():
        typ, desc, default_val = _parse_annotation(
            annotation, getattr(cls, name, inspect._empty)
        )
        desc = overrides.get(
            name, yaml_dict.get('attributes', {}).get(name, desc)
        )
        first = f'{name} : {typ}'
        if default_val is not inspect._empty:
            first += f', default is `{default_val!r}`'
        attr_lines.append(first)
        if desc:
            attr_lines.append(f'    {desc}')

    doc_parts = [narrative] if narrative else []
    if attr_lines:
        doc_parts.append('Attributes\n----------\n' + '\n'.join(attr_lines))

    cls.__doc__ = '\n\n'.join(doc_parts).strip()

    # Auto-decorate methods
    for name, member in vars(cls).items():
        if name.startswith('__') or not callable(member):
            continue
        if getattr(member, _SENTINEL, False):
            continue
        setattr(cls, name, apply(member))

    setattr(cls, _SENTINEL, True)
    return cls


# ---------------------------------------------------------------------------
# Function / method decoration
# ---------------------------------------------------------------------------


def _decorate_func(
    func: Callable[P, R],
    param_over: Dict[str, str],
    returns_over: Optional[Union[str, List[str]]],
) -> Callable[P, R]:
    if getattr(func, _SENTINEL, False):
        return func

    yaml_dict = _parse_yaml(inspect.getdoc(func) or '')
    narrative = _narrative(yaml_dict)

    param_descs = {**yaml_dict.get('parameters', {}), **param_over}
    returns_desc = (
        returns_over
        if returns_over is not None
        else yaml_dict.get('returns', '')
    )

    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)

    # Parameters block
    p_lines: List[str] = []
    for name, param in sig.parameters.items():
        if name in {'self', 'cls'}:
            continue
        ann = hints.get(name, param.annotation)
        default_val = (
            param.default
            if param.default is not inspect.Parameter.empty
            else inspect._empty
        )
        typ, desc_from_ann, default_val = _parse_annotation(ann, default_val)
        desc = param_descs.get(name, desc_from_ann)
        line = f'{name} : {typ}'
        if default_val is not inspect._empty:
            line += f', default is `{default_val!r}`'
        p_lines.append(line)
        if desc:
            p_lines.append(f'    {desc}')
    param_block = '\n'.join(p_lines) or 'None'

    # Returns block
    ret_ann = hints.get('return', sig.return_annotation)
    ret_type, ret_desc, _ = _parse_annotation(ret_ann, inspect._empty)
    if returns_desc:
        ret_desc = (
            returns_desc
            if isinstance(returns_desc, str)
            else '; '.join(returns_desc)
        )
    if not ret_type or ret_type == 'None':
        returns_block = 'Returns\n-------\nNone'
    else:
        returns_block = 'Returns\n-------\n' + ret_type
        if ret_desc:
            returns_block += f'\n    {ret_desc}'

    doc_parts = [narrative] if narrative else []
    doc_parts.append('Parameters\n----------\n' + param_block)
    doc_parts.append(returns_block)

    func.__doc__ = '\n\n'.join(doc_parts).strip()
    setattr(func, _SENTINEL, True)
    return func


# ---------------------------------------------------------------------------
# Annotation helper
# ---------------------------------------------------------------------------


def _parse_annotation(annotation: Any, default: Any) -> tuple[str, str, Any]:
    desc = ''
    typ_name = ''

    if get_origin(annotation) is Annotated:
        base, *meta = get_args(annotation)
        typ_name = _type_to_str(base)
        for m in meta:
            if isinstance(m, str):
                desc = m
                break
            if hasattr(m, 'description'):
                desc = m.description
                break
    elif annotation is inspect._empty:
        typ_name = 'Any'
    else:
        typ_name = _type_to_str(annotation)

    return typ_name, desc, default


def _type_to_str(tp: Any) -> str:
    origin = get_origin(tp)
    if origin is None:
        return getattr(tp, '__name__', str(tp))
    args = ', '.join(_type_to_str(arg) for arg in get_args(tp))
    return f'{origin.__name__}[{args}]'
