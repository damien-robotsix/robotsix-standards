# robotsix-standards

Cross-cutting conventions for the robotsix stack — how every service handles
**configuration** and the **three deployment modes** (uv package install, local
dev docker, and the central-deploy system) so an operator configures a service
the same way no matter how it runs.

This repo is both **the standard** (docs under `docs/`) and **the reference
implementation** (`robotsix-config`, a small shared library that makes the
config standard true by construction).

## Why this exists

A survey of the stack (`robotsix-central-deploy`, `robotsix-auto-mail`,
`robotsix-llmio`, `robotsix-mill`) found that **no two repos agreed** on the
config mechanism, precedence order, config-path variable name, secret
representation, or image registry. That makes the stack hard to learn and
operate, and impossible to share config tooling across. These standards fix
that.

## Documents

| Doc | What it covers |
|---|---|
| [Config standard](docs/config-standard.md) | One YAML+env config model, fixed precedence, one secret convention — the same in all three deploy modes. |
| [Packaging standard](docs/packaging-standard.md) | `requires-python`, console scripts, library-vs-service tiers, image registry & tags. |
| [Deploy contract](docs/deploy-contract.md) | The `deploy/docker-compose.yml` shape central-deploy consumes (authoritative reference). |
| [Integrating a service](docs/integrating-a-service.md) | Task-oriented how-to: take a repo from zero to a central-deploy one-click deploy. |
| [Entrypoint contract](docs/entrypoint-contract.md) | The shared container `entrypoint.sh` behavior. |

## The `robotsix-config` library

```python
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict
from robotsix_config import RobotsixConfig, emit_deploy_template, write_config_file


class MailConfig(RobotsixConfig):
    model_config = SettingsConfigDict(
        env_prefix="ROBOTSIX_MAIL_", env_nested_delimiter="__", extra="ignore"
    )
    log_level: str = "info"
    password: SecretStr = SecretStr("")


cfg = MailConfig()                      # defaults < config.yaml < env < kwargs
print(emit_deploy_template(MailConfig)) # -> central-deploy config/config.yaml template
```

Resolution order (lowest -> highest): **built-in defaults < `config.yaml` <
`ROBOTSIX_` env overlay < explicit kwargs**. The YAML file is located by one
variable, `ROBOTSIX_CONFIG_FILE` (default `config/config.yaml`). Secrets are
`pydantic.SecretStr` (masked on read); `write_config_file` persists config
`0600` in a `0700` directory.

## Development

```sh
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run mypy src
```

## Status

Draft for review. The standards describe the target state; migration of each
service is incremental and non-breaking (see the rollout section of the config
standard).

## License

MIT — see [LICENSE](LICENSE).
