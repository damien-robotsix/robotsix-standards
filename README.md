# robotsix-standards

Shared conventions for the robotsix stack, so any repository — whoever wrote it,
whenever — is configured, packaged, tested, and (if deployable) shipped the same
predictable way.

This repo holds **the standard** (docs under `docs/`). The shared library that
implements the config standard lives in
[`robotsix-yaml-config`](https://github.com/damien-robotsix/robotsix-yaml-config)
— its cascade primitives plus the optional `[pydantic]` schema layer
(`load_config`, `emit_deploy_template`, the `ROBOTSIX_CONFIG_FILE` convention,
the `0600` writer). One library, not two.

## Why this exists

As a stack grows, each repository tends to solve the same recurring problems —
config loading, packaging and versioning, CI and security gates, deployment — in
its own slightly different way. Every repo becomes a small dialect: contributors
relearn conventions each time, tooling and CI get reinvented, and operators face
per-repo guesswork. These standards define one way to do each, so consistency is
the default.

## Two scopes

**Every repository** (libraries and deployable components):

| Doc | What it covers |
|---|---|
| [Repo baseline](docs/repo-baseline.md) | uv tooling, `requires-python`, distribution tiers, changelog/module hygiene, CI & security gates, license. |

**Deployable components** (additionally):

| Doc | What it covers |
|---|---|
| [Component standard](docs/component-standard.md) | The three deploy modes, image registry & tags, the two compose files. |
| [Config standard](docs/config-standard.md) | One config model, fixed precedence, one secret convention — the same in all three deploy modes. |
| [Docker build & release](docs/docker-standard.md) | One Dockerfile pattern + one shared publish workflow → GHCR, with attestation and scanning. |
| [Deploy contract](docs/deploy-contract.md) | The `deploy/docker-compose.yml` shape the deployment system consumes (authoritative reference). |
| [Entrypoint contract](docs/entrypoint-contract.md) | The shared container `entrypoint.sh` behavior. |
| [Integrating a service](docs/integrating-a-service.md) | Task-oriented how-to: zero to a one-click deploy. |

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
