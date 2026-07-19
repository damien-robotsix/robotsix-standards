# robotsix-standards

Shared conventions for the robotsix stack, so any repository — whoever wrote it,
whenever — is configured, packaged, tested, and (if deployable) shipped the same
predictable way.

This repo ([`damien-robotsix/robotsix-standards`](https://github.com/damien-robotsix/robotsix-standards))
holds **the standard** (docs under `docs/`) — the canonical target of the
standards link every fleet README and AGENT.md carries. The shared library that
implements the config standard lives in
[`robotsix-config`](https://github.com/damien-robotsix/robotsix-config)
— one pydantic model, one JSON file (`load_config`, `dump_config`,
`config_schema_json`), the `ROBOTSIX_CONFIG_FILE` convention, and the `0600`
writer. One library, not two.

Published at [damien-robotsix.github.io/robotsix-standards](https://damien-robotsix.github.io/robotsix-standards/).

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
| [Repo baseline](docs/repo-baseline.md) | Distribution tiers, changelog/module hygiene, CI & security gates, license — language-agnostic. |
| [Security posture](docs/security-posture.md) | Self-enforcing security gates (SAST, dependency review, Dependabot, workflow hardening, secret protection, SBOM), auditable per repo. |
| [Docstring convention](docs/docstrings.md) | Python docstring style and coverage rules for all public modules, classes, and functions. |
| [Hypothesis testing](docs/hypothesis.md) | Property-based testing profiles, shared strategies module, and CI integration for repos that use Hypothesis. |
| [Python practices](docs/python.md) | uv, hatchling, `requires-python`, lint/type/security gates, test layout, pre-commit hooks. |
| [JavaScript practices](docs/javascript.md) | Vanilla frontend JS as static assets, lockfile discipline, vitest coverage floor, eslint/stylelint. |
| [ROS 2 practices](docs/ros2.md) | Workspace-skeleton layout, vcs2l manifest, devcontainer, colcon/rosdep build, lint gates. |

**Deployable components** (additionally):

| Doc | What it covers |
|---|---|
| [Component standard](docs/component-standard.md) | The three deploy modes, no embedded auth (centralized at the gateway), image registry & tags, the two compose files. |
| [Config standard](docs/config-standard.md) | One config model, one file (no env overlay, no CLI merge), one secret convention — the same in all three deploy modes. |
| [Docker build & release](docs/docker-standard.md) | One Dockerfile pattern + one shared publish workflow → GHCR, with attestation and scanning. |
| [Deploy contract](docs/deploy-contract.md) | The `deploy/docker-compose.yml` shape the deployment system consumes (canonical copy lives in [central-deploy](https://github.com/damien-robotsix/robotsix-central-deploy/blob/main/docs/DEPLOY_CONTRACT.md)). |
| [Entrypoint contract](docs/entrypoint-contract.md) | Console script as PID 1 (exec-form `ENTRYPOINT`); `entrypoint.sh` only for genuine startup work. |
| [Integrating a service](docs/integrating-a-service.md) | Task-oriented how-to: zero to a one-click deploy. |
| [Chat access](docs/chat-access-standard.md) | A standard skill endpoint so the chat agent (`robotsix-chat`) can invoke operations on the component. |
| [HTTP error envelope](docs/http-error-envelope.md) | One consistent RFC 9457 `application/problem+json` envelope for every error response, registered via centralized exception handlers. |

**The deployment system** (central-deploy only):

| Doc | What it covers |
|---|---|
| [Deployment system](docs/deployment-system.md) | The bootstrap tier: which standards central-deploy follows and which it is exempt from, and why. |

## The shared library

The config standard is implemented by
[`robotsix-config`](https://github.com/damien-robotsix/robotsix-config),
which every service depends on:

```python
from pydantic import BaseModel, SecretStr
from robotsix_config import config_schema_json, load_config


class MailConfig(BaseModel):
    log_level: str = "info"
    password: SecretStr = SecretStr("")


# The one file (ROBOTSIX_CONFIG_FILE, default config/config.json) is the only
# source of values; the model's defaults fill anything the file omits.
# No env overlay, no CLI merge.
cfg = load_config(MailConfig)
print(config_schema_json(MailConfig))  # -> commit as config/config.schema.json
```

The JSON file is located by one variable, `ROBOTSIX_CONFIG_FILE` (default
`config/config.json`). Secrets are `pydantic.SecretStr` (masked on read);
`robotsix_config.dump_config` persists config `0600` in a `0700`
directory. See the [config standard](docs/config-standard.md) for the full rule.

All fleet repos and their docs sites are indexed in [docs/fleet.md](docs/fleet.md).

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
