"""
doxs: A documentation helper library that generates and updates docstrings
from type annotations and decorator parameters.

Usage
-----
Example 1 (Using decorator parameters):

    import doxs

    @doxs.apply(class_vars={"var_1": "My var 1", "var_2": "My var 2"})
    class MyClass:
        var_1: int
        var_2: int

        @doxs.apply(params={"var_1": "My var 1", "var_2": "My var 2"},
                    returns=["The sum of var_1 and var_2"])
        def add(self, var_1: int, var_2: int) -> int:
            return var_1 + var_2

Example 2 (Using Annotation in type hints):

    import doxs

    @doxs.apply
    class MyClass:
        var_1: doxs.Annotation(int, "My var_1", default=1) = 1
        var_2: doxs.Annotation(int, "My var_2", default=2) = 2

        def add(
            self,
            var_1: doxs.Annotation(int, "My var_1", default=20) = 20,
            var_2: doxs.Annotation(int, "My var_2", default=30) = 30
        ) -> doxs.Annotation(int, "Sum of var_1 and var_2"):
            return var_1 + var_2
"""

import inspect
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Type,
    Union,
    get_type_hints,
)

# =============================================================================
# Annotation class
# =============================================================================
class Annotation:
    """
    A wrapper for type annotations that carries descriptive documentation.

    Parameters
    ----------
    type_ : type
        The actual type of the annotated element.
    description : str
        A description of the element.
    default : Any, optional
        The default value of the element.
    """

    def __init__(self, type_: Type, description: str, default: Any = None) -> None:
        self.type = type_
        self.description = description
        self.default = default

    def __repr__(self) -> str:
        return (
            f"Annotation({self.type.__name__}, {self.description!r}, "
            f"default={self.default!r})"
        )


# =============================================================================
# apply decorator
# =============================================================================
def apply(
    _obj: Any = None,
    *,
    class_vars: Optional[Dict[str, str]] = None,
    params: Optional[Dict[str, str]] = None,
    returns: Optional[Union[str, List[str]]] = None,
) -> Any:
    """
    Decorator to automatically generate and update docstrings from type annotations.

    This decorator can be applied to both classes and functions. For classes,
    an "Attributes" section is added to the docstring based on annotated class
    variables. For functions, "Parameters" and "Returns" sections are generated
    from the signature and type annotations.

    Parameters
    ----------
    class_vars : dict, optional
        Mapping of class variable names to additional description.
    params : dict, optional
        Mapping of function parameter names to additional description.
    returns : str or list of str, optional
        Description for the return value(s).

    Returns
    -------
    callable
        The decorated class or function with updated docstrings.
    """
    def decorator(obj: Any) -> Any:
        if inspect.isclass(obj):
            return _apply_to_class(obj, class_vars=class_vars)
        elif callable(obj):
            return _apply_to_func(obj, params=params, returns=returns)
        else:
            return obj

    if _obj is None:
        return decorator
    else:
        return decorator(_obj)


# =============================================================================
# Internal helper functions
# =============================================================================
def _apply_to_class(cls: Type, *, class_vars: Optional[Dict[str, str]] = None) -> Type:
    """
    Update the class docstring with an "Attributes" section based on
    type annotations and optional extra documentation from `class_vars`.

    Parameters
    ----------
    cls : type
        The class to process.
    class_vars : dict, optional
        Additional documentation for class variables.

    Returns
    -------
    type
        The class with an updated docstring.
    """
    annotations = getattr(cls, '__annotations__', {})
    attr_docs = []

    for attr, attr_type in annotations.items():
        # Determine the type name, description, and default value.
        default = cls.__dict__.get(attr, None)
        desc = ""
        typ = ""

        if isinstance(attr_type, Annotation):
            typ = attr_type.type.__name__
            desc = attr_type.description
            if attr_type.default is not None:
                default = attr_type.default
        else:
            # For standard types, use the type name if available.
            typ = getattr(attr_type, "__name__", str(attr_type))

        # Allow overriding the description via class_vars.
        if class_vars and attr in class_vars:
            desc = class_vars[attr]

        doc_line = f"{attr} : {typ}"
        attr_docs.append(doc_line)
        if desc:
            attr_docs.append(f"    {desc}")
        # Only print default if it was explicitly provided.
        if attr in cls.__dict__:
            attr_docs.append(f"    Default: {default!r}")
        attr_docs.append("")  # Add spacing between attributes

    attr_doc_str = "\n".join(attr_docs).strip()

    original_doc = cls.__doc__ or ""
    new_doc_lines = [original_doc, "", "Attributes:", "-----------", "", attr_doc_str]
    cls.__doc__ = "\n".join(new_doc_lines).strip()

    # Automatically decorate callable methods that are not special methods.
    for attr_name, attr_value in cls.__dict__.items():
        if callable(attr_value) and not attr_name.startswith("__"):
            decorated = apply(attr_value)
            setattr(cls, attr_name, decorated)

    return cls


def _apply_to_func(
    func: Callable, *, params: Optional[Dict[str, str]] = None, returns: Optional[Union[str, List[str]]] = None
) -> Callable:
    """
    Update the function's docstring with "Parameters" and "Returns" sections based on
    type annotations and optional extra documentation from the decorator.

    Parameters
    ----------
    func : callable
        The function to process.
    params : dict, optional
        Additional parameter documentation.
    returns : str or list of str, optional
        Additional documentation for the return value.

    Returns
    -------
    callable
        The function with an updated docstring.
    """
    sig = inspect.signature(func)
    type_hints = get_type_hints(func)
    param_docs = []

    for name, param in sig.parameters.items():
        # Skip 'self' for methods.
        if name == "self":
            continue
        annotation = type_hints.get(name, param.annotation)
        if annotation is inspect.Parameter.empty:
            annotation = Any

        typ = ""
        desc = ""
        default = param.default if param.default is not inspect.Parameter.empty else None

        if isinstance(annotation, Annotation):
            typ = annotation.type.__name__
            desc = annotation.description
            if annotation.default is not None:
                default = annotation.default
        else:
            typ = getattr(annotation, "__name__", str(annotation))

        # Allow overriding description via decorator parameters.
        if params and name in params:
            desc = params[name]

        line = f"{name} : {typ}"
        param_docs.append(line)
        if desc:
            param_docs.append(f"    {desc}")
        if default is not None:
            param_docs.append(f"    Default: {default!r}")
        param_docs.append("")

    params_doc_str = "\n".join(param_docs).strip()

    # Process the return annotation.
    ret_annotation = type_hints.get("return", sig.return_annotation)
    if ret_annotation is inspect.Signature.empty:
        ret_annotation = type(None)
    ret_type = ""
    ret_desc = ""
    if isinstance(ret_annotation, Annotation):
        ret_type = ret_annotation.type.__name__
        ret_desc = ret_annotation.description
    else:
        ret_type = getattr(ret_annotation, "__name__", str(ret_annotation))

    if returns:
        if isinstance(returns, list):
            ret_desc = "; ".join(returns)
        else:
            ret_desc = returns

    params_section = "Parameters:\n-----------\n" + (params_doc_str if params_doc_str else "None")
    returns_section = "Returns:\n--------\n"
    if ret_type and ret_type != "None":
        returns_section += f"{ret_type}"
        if ret_desc:
            returns_section += f"\n    {ret_desc}"
    else:
        returns_section += "None"

    original_doc = func.__doc__ or ""
    new_doc = "\n".join([original_doc, "", params_section, "", returns_section]).strip()

    @wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    wrapper.__doc__ = new_doc
    return wrapper
