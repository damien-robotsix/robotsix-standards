"""Emit the central-deploy ``config/config.yaml`` template from a config model.

The central-deploy contract (§8) represents a secret slot as an empty leaf
(``key: ""``) that the operator fills in the onboarding UI. Because the robotsix
config schema is the single source of truth, that template can be *generated*
from the model instead of hand-maintained — keeping the deploy template and the
runtime schema from ever drifting apart.
"""

from __future__ import annotations

import typing
from typing import Any

import yaml
from pydantic import BaseModel, SecretStr
from pydantic_core import PydanticUndefined

_TYPE_PLACEHOLDERS: dict[type, Any] = {
    str: "",
    int: 0,
    float: 0.0,
    bool: False,
}


def _is_secret(annotation: Any) -> bool:
    if annotation is SecretStr:
        return True
    return SecretStr in typing.get_args(annotation)


def _model_of(annotation: Any) -> type[BaseModel] | None:
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    for arg in typing.get_args(annotation):
        if isinstance(arg, type) and issubclass(arg, BaseModel):
            return arg
    return None


def _placeholder(annotation: Any) -> Any:
    origin = typing.get_origin(annotation)
    if origin in (list, set, tuple):
        return []
    if origin is dict:
        return {}
    if isinstance(annotation, type):
        return _TYPE_PLACEHOLDERS.get(annotation)
    # Optional[...] / Union — use the first concrete arg's placeholder.
    for arg in typing.get_args(annotation):
        if arg is type(None):
            continue
        return _placeholder(arg)
    return None


def _model_to_template(model_cls: type[BaseModel]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for name, field in model_cls.model_fields.items():
        key = field.alias or name
        annotation = field.annotation

        if _is_secret(annotation):
            out[key] = ""  # secret slot — operator fills it
            continue

        nested = _model_of(annotation)
        if nested is not None:
            out[key] = _model_to_template(nested)
            continue

        if field.default is not PydanticUndefined:
            out[key] = _coerce(field.default)
        elif field.default_factory is not None:
            out[key] = _coerce(field.default_factory())  # type: ignore[call-arg]
        else:
            out[key] = _placeholder(annotation)
    return out


def _coerce(value: Any) -> Any:
    """Render a default value into a YAML-friendly plain type."""
    if isinstance(value, SecretStr):
        return ""
    if isinstance(value, BaseModel):
        return {k: _coerce(v) for k, v in value.model_dump().items()}
    return value


def emit_deploy_template(model_cls: type[BaseModel]) -> str:
    """Return a central-deploy ``config/config.yaml`` template for *model_cls*.

    Secret fields (``SecretStr``) become empty-string slots; everything else
    carries its default (or a type-appropriate placeholder when required).
    Nested models become nested mappings.
    """
    data = _model_to_template(model_cls)
    return yaml.safe_dump(data, default_flow_style=False, sort_keys=False)
