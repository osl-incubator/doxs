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
    Type,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

import yaml

from typing_extensions import ParamSpec

__all__ = ['DocString', 'apply']
_SENTINEL = '__doxs_applied__'

T = TypeVar('T', bound=type)
P = ParamSpec('P')
R = TypeVar('R')


def _parse_yaml_doc(raw: Optional[str]) -> Dict[str, Any]:
    if not raw or ':' not in raw:
        return {}
    try:
        data = yaml.safe_load(textwrap.dedent(raw))
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _compose_narrative(yaml_data: Dict[str, Any]) -> str:
    """Build plain-text *title/summary* block from YAML."""

    title = str(yaml_data.get('title', '')).strip()
    summary = str(yaml_data.get('summary', '')).rstrip()

    parts: List[str] = []
    if title:
        parts.append(title if title.endswith('.') else title + '.')
    if summary:
        # Already multi-line (from ``|``): keep as-is; else treat as one-liner.
        if '\n' in summary:
            parts.append(summary)
        else:
            parts.append(summary)
    return '\n\n'.join(parts).strip()


@dataclass
class DocString:
    description: str


def apply(
    _obj: Any = None,
    *,
    # Back-compat kwargs (optional)
    class_vars: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    returns: Optional[Union[str, List[str]]] = None,
) -> Any:
    """Decorate a class or function and inject numpydoc blocks.

    Preferred usage expects metadata to be provided inside a YAML docstring,
    but legacy kwargs (*class_vars*, *params*, *returns*) are still honoured
    and override YAML values when given.
    """

    def decorator(obj: Any) -> Any:
        if inspect.isclass(obj):
            return _apply_to_class(
                obj, yaml_first=True, overrides=class_vars or {}
            )
        if callable(obj):
            return _apply_to_func(
                obj, yaml_first=True, params=params, returns=returns
            )
        return obj

    return decorator if _obj is None else decorator(_obj)


def _apply_to_class(
    cls: T, *, yaml_first: bool, overrides: Dict[str, str]
) -> T:
    if getattr(cls, _SENTINEL, False):
        return cls

    yaml_data = _parse_yaml_doc(inspect.getdoc(cls)) if yaml_first else {}
    narrative = _compose_narrative(yaml_data)

    _inject_attributes_section(
        cls, {**yaml_data.get('attributes', {}), **overrides}
    )

    # Merge narrative first (before auto-decorating methods)
    cls.__doc__ = _merge_docstring(narrative, cls.__doc__ or '')

    for name, member in vars(cls).items():
        if name.startswith('__') or not callable(member):
            continue
        if getattr(member, _SENTINEL, False):
            continue
        setattr(cls, name, apply(member))

    setattr(cls, _SENTINEL, True)
    return cls


def _apply_to_func(
    func: Callable[P, R],
    *,
    yaml_first: bool,
    params: Optional[Dict[str, str]] = None,
    returns: Optional[Union[str, List[str]]] = None,
) -> Callable[P, R]:
    if getattr(func, _SENTINEL, False):  # idempotent
        return func

    raw_doc = inspect.getdoc(func) or ''
    yaml_data = _parse_yaml_doc(raw_doc)
    narrative = _compose_narrative(yaml_data)

    # Merge precedence - decorator kwargs override YAML
    param_descs = {**yaml_data.get('parameters', {}), **(params or {})}
    returns_desc = (
        returns if returns is not None else yaml_data.get('returns', '')
    )

    sig = inspect.signature(func)
    hints = get_type_hints(func, include_extras=True)

    # ---------------- "Parameters" block ----------------
    param_lines: List[str] = []
    for name, param in sig.parameters.items():
        if name in {'self', 'cls'}:
            continue

        annotation = hints.get(name, param.annotation)
        default_val = (
            param.default
            if param.default is not inspect.Parameter.empty
            else inspect._empty
        )

        typ, desc_from_ann, default_val = _parse_annotation(
            annotation, default_val
        )
        desc = param_descs.get(name, desc_from_ann or '')

        first = f'{name} : {typ}'
        if default_val is not inspect._empty:
            first += f', default is `{default_val!r}`'
        param_lines.append(first)
        if desc:
            param_lines.append(f'    {desc}')

    param_block = '\n'.join(param_lines) or 'None'

    # ------------------ "Returns" block ------------------
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

    generated_sections = (
        f'Parameters\n----------\n{param_block}\n\n{returns_block}'
    )

    # Build final docstring: narrative + two line breaks + generated sections
    final_doc = (narrative.strip() + '\n\n' + generated_sections).strip()

    func.__doc__ = final_doc
    setattr(func, _SENTINEL, True)
    return func


def _inject_attributes_section(
    cls: Type[Any], descriptions: Dict[str, str]
) -> None:
    annotations = getattr(cls, '__annotations__', {})
    if not annotations:
        return

    lines: List[str] = []
    for name, annotation in annotations.items():
        typ, desc, default_val = _parse_annotation(
            annotation, getattr(cls, name, inspect._empty)
        )
        if name in descriptions:
            desc = descriptions[name]

        first = f'{name} : {typ}'
        if default_val is not inspect._empty:
            first += f', default is `{default_val!r}`'
        lines.append(first)
        if desc:
            lines.append(f'    {desc}')

    if lines:
        cls.__doc__ = _merge_docstring(
            cls.__doc__, 'Attributes\n----------\n' + '\n'.join(lines)
        )


def _parse_annotation(annotation: Any, default: Any) -> tuple[str, str, Any]:
    """Parse annotation."""
    desc = ''
    typ_name = ''

    if get_origin(annotation) is Annotated:
        base_type, *metadata = get_args(annotation)
        typ_name = _type_to_str(base_type)

        for meta in metadata:
            if isinstance(meta, str):
                desc = meta
                break
            if hasattr(meta, 'description'):
                desc = getattr(meta, 'description')
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


def _merge_docstring(original: Optional[str], generated: str) -> str:
    original = original or ''
    return (
        original.strip()
        if generated in original
        else (original.rstrip() + '\n\n' + generated).strip()
    )
