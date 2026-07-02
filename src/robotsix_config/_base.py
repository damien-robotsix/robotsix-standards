"""The ``RobotsixConfig`` base settings class and config-file resolution.

Precedence (lowest → highest):

    built-in defaults  <  config.yaml  <  ROBOTSIX_ env overlay  <  explicit kwargs

Implemented by ordering pydantic-settings sources so that ``init`` (explicit
kwargs, i.e. the CLI layer) wins, then the ``ROBOTSIX_<SERVICE>_`` environment
overlay, then the YAML file, then the model's own field defaults.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

#: Environment variable naming the YAML config file. One name for every service.
CONFIG_FILE_ENV = "ROBOTSIX_CONFIG_FILE"

#: Default config path when :data:`CONFIG_FILE_ENV` is unset.
DEFAULT_CONFIG_PATH = Path("config/config.yaml")


def resolve_config_path() -> Path:
    """Return the config-file path from :data:`CONFIG_FILE_ENV` or the default.

    The path is *not* required to exist — a missing file simply means the
    config resolves from defaults + the environment overlay.
    """
    raw = os.environ.get(CONFIG_FILE_ENV)
    return Path(raw) if raw else DEFAULT_CONFIG_PATH


def _read_yaml(path: Path) -> dict[str, Any]:
    """Load a YAML mapping from *path*; ``{}`` if it is missing or empty."""
    if not path.is_file():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError(
            f"config file {path} must contain a YAML mapping at the top level, "
            f"got {type(loaded).__name__}"
        )
    return loaded


class _RobotsixYamlSource(PydanticBaseSettingsSource):
    """A pydantic-settings source backed by the resolved YAML config file."""

    def __init__(self, settings_cls: type[BaseSettings], path: Path) -> None:
        super().__init__(settings_cls)
        self._data = _read_yaml(path)

    def get_field_value(
        self, field: Any, field_name: str
    ) -> tuple[Any, str, bool]:  # pragma: no cover - not used; __call__ overrides
        value = self._data.get(field_name)
        return value, field_name, value is not None

    def __call__(self) -> dict[str, Any]:
        return self._data


class RobotsixConfig(BaseSettings):
    """Base class for every robotsix service's configuration model.

    Subclass it, set a per-service env prefix, and declare fields (using
    :class:`pydantic.SecretStr` for secrets)::

        from pydantic import SecretStr
        from pydantic_settings import SettingsConfigDict
        from robotsix_config import RobotsixConfig

        class MailConfig(RobotsixConfig):
            model_config = SettingsConfigDict(
                env_prefix="ROBOTSIX_MAIL_",
                env_nested_delimiter="__",
                extra="ignore",
            )
            host: str = "localhost"
            password: SecretStr = SecretStr("")

    Then ``MailConfig()`` resolves defaults → ``config.yaml`` → env → kwargs.
    """

    model_config = SettingsConfigDict(
        env_prefix="ROBOTSIX_",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Order sources so kwargs > env > YAML file > model defaults.

        pydantic-settings applies earlier sources at higher precedence, so the
        YAML source is inserted just above ``file_secret_settings`` (which sits
        below everything and supplies nothing unless a secrets dir is used).
        """
        yaml_source = _RobotsixYamlSource(settings_cls, resolve_config_path())
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            yaml_source,
            file_secret_settings,
        )
