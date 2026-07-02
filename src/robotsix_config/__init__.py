"""robotsix-config — the shared configuration model for the robotsix stack.

One config schema per service, defined once with pydantic, that resolves the
same way in all three deploy modes (pip / dev docker / central-deploy):

    built-in defaults  <  config.yaml  <  ROBOTSIX_ env overlay  <  explicit kwargs

The YAML file is located by a single environment variable
(:data:`CONFIG_FILE_ENV`, default ``config/config.yaml``), secrets are declared
with :class:`pydantic.SecretStr` (masked on read), and the same schema can emit
the central-deploy ``config/config.yaml`` template via
:func:`emit_deploy_template`.

See the ``config-standard`` document in this repo for the full rationale.
"""

from __future__ import annotations

from ._base import (
    CONFIG_FILE_ENV,
    DEFAULT_CONFIG_PATH,
    RobotsixConfig,
    resolve_config_path,
)
from ._secrets import write_config_file
from ._template import emit_deploy_template

__all__ = [
    "CONFIG_FILE_ENV",
    "DEFAULT_CONFIG_PATH",
    "RobotsixConfig",
    "emit_deploy_template",
    "resolve_config_path",
    "write_config_file",
]
