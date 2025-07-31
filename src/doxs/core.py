"""
Doxs core library.

A small helper library that turns type-hints into *numpydoc*-style
sections and injects them into docstrings.

"""

from __future__ import annotations

import inspect

from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

__all__ = ['Annotation', 'apply']
_SENTINEL = '__doxs_applied__'


class Annotation:
    """Wrap a type annotation with extra metadata.

    Parameters
    ----------
    type_ : type
        The underlying Python type.
    description : str
        Human-readable description.
    default : Any, optional
        Optional default value (``inspect._empty`` means *no default*).
    """

    def __init__(
        self, type_: Type, description: str, default: Any = inspect._empty
    ) -> None:
        """Initialize class instance."""
        self.type = type_
        self.description = description
        self.default = default

    def __repr__(self) -> str:  # pragma: no cover
        """Return the object representation."""
        default_repr = (
            '…' if self.default is inspect._empty else repr(self.default)
        )
        return (
            f'Annotation({self.type.__name__}, '
            f'{self.description!r}, default={default_repr})'
        )


def apply(
    _obj: Any = None,
    *,
    class_vars: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    returns: Optional[Union[str, List[str]]] = None,
) -> Any:
    """
    Decorate a *class* or *function* to auto-generate numpydoc sections.

    When decorating a **class** an *Attributes* section is derived from the
    annotated class variables. Decorating a **function or method** adds
    *Parameters* and *Returns* sections.

    Notes
    -----
    The decorator is *idempotent* - running it multiple times will not
    duplicate the generated sections.
    """

    def decorator(obj: Any) -> Any:
        if inspect.isclass(obj):
            return _apply_to_class(obj, class_vars=class_vars)
        if callable(obj):
            return _apply_to_func(obj, params=params, returns=returns)
        return obj

    if _obj is None:
        return decorator
    return decorator(_obj)


def _apply_to_class(
    cls: Type, *, class_vars: Optional[Dict[str, str]] = None
) -> Type:
    """Inject an *Attributes* section into *cls*'s docstring."""
    if getattr(cls, _SENTINEL, False):
        return cls

    _inject_attributes_section(cls, class_vars or {})

    # Auto-decorate methods that have not been explicitly decorated.
    for name, member in vars(cls).items():
        if name.startswith('__') or not callable(member):
            continue
        if getattr(member, _SENTINEL, False):
            continue
        setattr(cls, name, apply(member))

    setattr(cls, _SENTINEL, True)
    return cls


def _apply_to_func(
    func: Callable,
    *,
    params: Optional[Dict[str, str]] = None,
    returns: Optional[Union[str, List[str]]] = None,
) -> Callable:
    """Inject *Parameters* and *Returns* sections into *func*'s docstring."""
    if getattr(func, _SENTINEL, False):
        return func

    params = params or {}

    sig = inspect.signature(func)
    type_hints = get_type_hints(func)

    # ---------------------------- parameters ----------------------------- #
    param_lines: List[str] = []
    for name, param in sig.parameters.items():
        if name in {'self', 'cls'}:  # skip implicit parameters
            continue

        annotation = type_hints.get(name, param.annotation)
        default = (
            param.default
            if param.default is not inspect.Parameter.empty
            else inspect._empty
        )

        typ, desc, default = _parse_annotation(annotation, default)
        if name in params:
            desc = params[name]

        param_lines.append(f'{name} : {typ}')
        if desc:
            param_lines.append(f'    {desc}')
        if default is not inspect._empty:
            param_lines.append(f'    Default: {default!r}')
        param_lines.append('')

    param_block = '\n'.join(param_lines).rstrip() or 'None'

    # ----------------------------- returns ------------------------------ #
    ret_ann = type_hints.get('return', sig.return_annotation)
    ret_type, ret_desc, _ = _parse_annotation(ret_ann, inspect._empty)

    if returns is not None:
        ret_desc = '; '.join(returns) if isinstance(returns, list) else returns

    if not ret_type or ret_type == 'None':
        returns_block = 'Returns:\n--------\nNone'
    else:
        returns_block = 'Returns:\n--------\n' + ret_type
        if ret_desc:
            returns_block += f'\n    {ret_desc}'

    generated = f'Parameters:\n-----------\n{param_block}\n\n{returns_block}'

    func.__doc__ = _merge_docstring(func.__doc__, generated)
    setattr(func, _SENTINEL, True)
    return func


def _inject_attributes_section(cls: Type, overrides: Dict[str, str]) -> None:
    annotations = getattr(cls, '__annotations__', {})
    if not annotations:
        return

    lines: List[str] = []
    for name, annotation in annotations.items():
        typ, desc, default = _parse_annotation(
            annotation, getattr(cls, name, inspect._empty)
        )
        if name in overrides:
            desc = overrides[name]

        lines.append(f'{name} : {typ}')
        if desc:
            lines.append(f'    {desc}')
        if default is not inspect._empty:
            lines.append(f'    Default: {default!r}')
        lines.append('')

    block = '\n'.join(lines).rstrip()
    attributes_block = f'Attributes:\n-----------\n{block}'

    cls.__doc__ = _merge_docstring(cls.__doc__, attributes_block)


def _parse_annotation(annotation: Any, default: Any):
    """Return ``(type_name, description, default)`` from *annotation*."""
    desc = ''
    typ_name = ''

    if isinstance(annotation, Annotation):
        typ_name = annotation.type.__name__
        desc = annotation.description
        default = (
            annotation.default
            if annotation.default is not inspect._empty
            else default
        )
    elif annotation is inspect._empty:
        typ_name = 'Any'
    else:
        typ_name = _type_to_str(annotation)

    return typ_name, desc, default


def _type_to_str(tp: Any) -> str:
    """Return a readable representation for *typing* annotations."""
    origin = get_origin(tp)
    if origin is None:
        return getattr(tp, '__name__', str(tp))

    args = ', '.join(_type_to_str(arg) for arg in get_args(tp))
    return f'{origin.__name__}[{args}]'


def _merge_docstring(original: Optional[str], generated: str) -> str:
    """Append *generated* block if it's not already present."""
    original = original or ''
    if generated in original:
        return original.strip()
    return (original.rstrip() + '\n\n' + generated).strip()
