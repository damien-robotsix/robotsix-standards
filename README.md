# robotsix-standards

Cross-cutting conventions for the robotsix stack — how every service handles
**configuration** and the **three deployment modes** (uv package install, local
dev docker, and the central-deploy system) so an operator configures a service
the same way no matter how it runs.

This repo holds **the standard** (docs under `docs/`). The shared library that
makes the config standard true by construction lives in
[`robotsix-yaml-config`](https://github.com/damien-robotsix/robotsix-yaml-config)
— its cascade primitives plus the optional `[pydantic]` schema layer
(`load_config`, `emit_deploy_template`, the `ROBOTSIX_CONFIG_FILE` convention,
the `0600` writer). One library, not two.

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

## The shared library

The config standard is implemented by
[`robotsix-yaml-config`](https://github.com/damien-robotsix/robotsix-yaml-config)
(its `[pydantic]` extra), which every service depends on:

```python
from pydantic import BaseModel, SecretStr
from robotsix_yaml_config.schema import load_config, emit_deploy_template


class MailConfig(BaseModel):
    log_level: str = "info"
    password: SecretStr = SecretStr("")


cfg = load_config(MailConfig, env_prefix="ROBOTSIX_MAIL")
# defaults < config.yaml < ROBOTSIX_MAIL_ env overlay < overrides
print(emit_deploy_template(MailConfig))  # -> central-deploy config/config.yaml template
```

The YAML file is located by one variable, `ROBOTSIX_CONFIG_FILE` (default
`config/config.yaml`). Secrets are `pydantic.SecretStr` (masked on read);
`robotsix_yaml_config.write_config_file` persists config `0600` in a `0700`
directory. See the [config standard](docs/config-standard.md) for the full rule.

## Building the docs

```sh
uv run --group docs mkdocs build --strict
```

## Status

Draft for review. The standards describe the target state; migration of each
service is incremental and non-breaking (see the rollout section of the config
standard).

## License

MIT — see [LICENSE](LICENSE).
