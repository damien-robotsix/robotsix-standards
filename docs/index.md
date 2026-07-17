# robotsix stack standards

Shared conventions for the robotsix stack, so that any repository — whoever
wrote it, whenever — is configured, packaged, tested, and (if deployable)
shipped in the same predictable way.

## Why this exists

As a stack grows, each repository tends to solve the same recurring problems —
how configuration is loaded and where it lives, how packages are installed and
versioned, how CI and security gates are wired, and how a service is deployed —
in its own slightly different way. Left unchecked, every repo becomes a small
dialect: contributors relearn the conventions each time, tooling and CI get
reinvented instead of shared, and operators face per-repo guesswork.

These standards define one way to do each of those things. The payoff is
consistency: moving between repos is cheap, tooling and workflows are shared
rather than duplicated, and a config or deploy setup learned once transfers
everywhere.

## Two scopes

### Every repository (libraries and deployable components)

- **[Repo baseline](repo-baseline.md)** — distribution tiers, changelog and
  module-registration hygiene, CI and security gates, licensing.
- **[Security posture](security-posture.md)** — self-enforcing security gates
  (SAST, dependency review, Dependabot, workflow hardening, secret protection,
  SBOM), auditable per repo.
- **[Python practices](python.md)** — uv, hatchling, `requires-python` policy,
  lint/type/security gates, test layout, pre-commit hooks.
- **[JavaScript practices](javascript.md)** — vanilla frontend JS as static
  assets, lockfile discipline, vitest coverage floor, eslint/stylelint.
- **[ROS 2 practices](ros2.md)** — workspace-skeleton layout, vcs2l manifest,
  devcontainer, colcon/rosdep build, lint gates.

### Deployable components (additionally)

A *deployable component* ships a runnable service (a container image) and
integrates with the deployment system. Beyond the baseline it follows:

- **[Component standard](component-standard.md)** — the three deploy modes,
  no embedded auth (centralized at the gateway), image registry & tags, the
  two compose files.
- **[Config standard](config-standard.md)** — one config model that resolves the
  same way across all deploy modes.
- **[Docker build & release](docker-standard.md)** — one Dockerfile pattern and
  one publish workflow to a single registry.
- **[Deploy contract](deploy-contract.md)** — the `deploy/docker-compose.yml`
  shape the deployment system consumes.
- **[Entrypoint contract](entrypoint-contract.md)** — how a component's
  container starts up.
- **[Integrating a service](integrating-a-service.md)** — the end-to-end how-to.
- **[Chat access](chat-access-standard.md)** — a standard skill endpoint so the
  chat agent can invoke operations on the component.

### The deployment system (bootstrap tier)

One repo — `robotsix-central-deploy` — is the deployment system itself and
cannot be deployed through itself:

- **[Deployment system](deployment-system.md)** — which standards it follows
  (baseline, docker build & release, entrypoint contract) and which it is
  exempt from (deploy contract, config standard), and why.

## Which am I?

- **Library** — imported by other packages, no runnable service of its own.
  Follow the **repo baseline** only.
- **Deployable component** — ships a service/container. Follow the **repo
  baseline** *and* the **component** standards.
- **The deployment system** — central-deploy only. Follow the
  [deployment-system tier](deployment-system.md).

## The fleet

Every repo, what it is, and where its docs live: **[the fleet page](fleet.md)**.

## Reference implementation

The config standard is implemented by the shared configuration library
([`robotsix-config`](https://github.com/damien-robotsix/robotsix-config)):
`load_config` loads **the one config file** (`ROBOTSIX_CONFIG_FILE`, default
`config/config.json`) into a validated pydantic model — the file is the only
source of values, the model's defaults fill the rest; no env overlay, no CLI
merge — with secret masking (`SecretStr`), a `0600` config writer
(`dump_config`), and a JSON-Schema emitter (`config_schema_json`) for the
deploy UI. One shared library, already a stack dependency.

## Changing the standards

The standards change through the mill, like everything else:

- **File a ticket on the `robotsix-standards` board** — for a gap, a
  contradiction with fleet reality, or an incident whose post-mortem traces
  to a standards flaw (the 2026-07-03 claude-mount outage is the worked
  example: outage → standards change → fleet tickets, same day).
- The ticket follows the normal mill pipeline; **the approval gate is the
  operator's decision point**. A standard nobody approved is a suggestion.
- An accepted change lands as **one docs PR plus fleet-alignment tickets** —
  a standards change with no tickets is a wish.
- **Clean cutover is the default** for every migration: no compatibility
  shims, no aliases; data moves by hand, case by case.
- **Supersession is normal.** When reality reverses a decision, the new text
  references what it replaces — openly, not by silent rewrite.
