# robotsix stack standards

Cross-cutting conventions for the robotsix stack: how every service handles
**configuration** and the **three deployment modes** (uv package install, local
dev docker, and central-deploy) so a service is configured the same way no
matter how it runs.

## The problem these standards solve

A cross-repo survey of `robotsix-central-deploy`, `robotsix-auto-mail`,
`robotsix-llmio`, and `robotsix-mill` found **no two repos agreed** on:

- the config mechanism (env-only vs YAML-only vs YAML+env),
- the precedence order (some make env beat the file, some make the file
  authoritative, some make the CLI win),
- the name of the config-path environment variable (`MAIL_CONFIG_PATH` vs
  `MILL_CONFIG_FILE` vs none),
- the secret representation (`""` vs a `SECRET` sentinel vs env-only),
- the image registry (GHCR vs Docker Hub vs PyPI vs none).

An operator who learns one service guesses wrong on the next. These standards
define one way, and ship a library that makes it true by construction.

## Read next

- **[Config standard](config-standard.md)** — the unified config model.
- **[Packaging standard](packaging-standard.md)** — packaging, tiers, registry, tags.
- **[Deploy contract](deploy-contract.md)** — the central-deploy compose contract.
- **[Integrating a service](integrating-a-service.md)** — the how-to.
- **[Entrypoint contract](entrypoint-contract.md)** — the container entrypoint.

## Reference implementation

The config standard is implemented by
[`robotsix-yaml-config`](https://github.com/damien-robotsix/robotsix-yaml-config)
(its `[pydantic]` extra): `load_config` resolves
`defaults < config.yaml < env < overrides` into a validated model, with secret
masking, a `0600` config writer, and a central-deploy template emitter. One
shared library, already a stack dependency.
