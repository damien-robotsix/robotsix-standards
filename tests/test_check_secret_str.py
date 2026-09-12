"""Unit tests for the SecretStr gate (scripts/check-secret-str.py).

The config standard (docs/config-standard.md §3) mandates that secret fields in
pydantic config models are declared with ``pydantic.SecretStr``.  This gate
makes that MUST machine-checkable: a secret-named field annotated ``str`` (or
``Optional[str]`` / ``str | None``) fails the hook.  These tests cover the
happy path (secret fields correctly typed ``SecretStr``), the violation cases
(plain ``str``, optional ``str``), and the edges that must not false-positive
(``public_key: str``, secret maps typed ``dict[str, SecretStr]``, non-model
classes, inherited models).
"""

from __future__ import annotations

from pathlib import Path

from types import ModuleType


def _write(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _fields(check_secret_str: ModuleType, source: str) -> list[str]:
    """Return ``Class.field`` strings flagged by scanning an in-memory source."""
    findings = check_secret_str.scan_file(_write(Path("/tmp"), "probe.py", source))
    return [f"{finding.cls}.{finding.field}" for finding in findings]


def test_secret_str_field_is_accepted(check_secret_str: ModuleType) -> None:
    source = """\
from pydantic import BaseModel, SecretStr


class MailConfig(BaseModel):
    password: SecretStr = SecretStr("")
    api_key: SecretStr = SecretStr("")
"""
    assert _fields(check_secret_str, source) == []


def test_plain_str_password_is_rejected(check_secret_str: ModuleType) -> None:
    source = """\
from pydantic import BaseModel


class MailConfig(BaseModel):
    password: str = ""
"""
    assert _fields(check_secret_str, source) == ["MailConfig.password"]


def test_secret_patterns_are_all_flagged(check_secret_str: ModuleType) -> None:
    source = """\
from pydantic import BaseModel


class SecretsConfig(BaseModel):
    api_key: str
    openrouter_token: str
    master_password: str
    client_secret: str
"""
    fields = _fields(check_secret_str, source)
    assert fields == [
        "SecretsConfig.api_key",
        "SecretsConfig.openrouter_token",
        "SecretsConfig.master_password",
        "SecretsConfig.client_secret",
    ]


def test_optional_str_secret_is_rejected(check_secret_str: ModuleType) -> None:
    source = """\
from pydantic import BaseModel


class SecretsConfig(BaseModel):
    api_key: Optional[str] = None
    password: str | None = None
"""
    fields = _fields(check_secret_str, source)
    assert fields == ["SecretsConfig.api_key", "SecretsConfig.password"]


def test_non_secret_str_field_is_accepted(check_secret_str: ModuleType) -> None:
    # public_key is deliberately public (config-standard.md §7) and must not
    # be flagged even though it carries "key".
    source = """\
from pydantic import BaseModel


class LangfuseProject(BaseModel):
    host: str = "localhost"
    public_key: str = ""
    secret_key: SecretStr = SecretStr("")
"""
    assert _fields(check_secret_str, source) == []


def test_secret_map_with_secretstr_values_is_accepted(
    check_secret_str: ModuleType,
) -> None:
    # dict[str, SecretStr] is the documented pattern for a secret map; the
    # container itself must not be mistaken for a scalar `str`.
    source = """\
from pydantic import BaseModel, SecretStr


class OpenRouterConfig(BaseModel):
    keys: dict[str, SecretStr] = {}
"""
    assert _fields(check_secret_str, source) == []


def test_non_model_class_is_ignored(check_secret_str: ModuleType) -> None:
    source = """\
class NotAPydanticModel:
    api_key: str = ""
"""
    assert _fields(check_secret_str, source) == []


def test_inherited_model_chain_is_checked(check_secret_str: ModuleType) -> None:
    source = """\
from pydantic import BaseModel


class BaseConfig(BaseModel):
    password: str = ""


class ChildConfig(BaseConfig):
    token: str = ""
"""
    fields = _fields(check_secret_str, source)
    assert fields == ["BaseConfig.password", "ChildConfig.token"]


def test_main_exit_codes(check_secret_str: ModuleType, tmp_path: Path) -> None:
    clean = _write(
        tmp_path,
        "clean_config.py",
        "from pydantic import BaseModel, SecretStr\n\n"
        "class Config(BaseModel):\n    password: SecretStr = SecretStr('')\n",
    )
    dirty = _write(
        tmp_path,
        "dirty_config.py",
        "from pydantic import BaseModel\n\n"
        "class Config(BaseModel):\n    api_key: str = ''\n",
    )

    assert check_secret_str.main([str(clean)]) == 0
    assert check_secret_str.main([str(dirty)]) == 1
