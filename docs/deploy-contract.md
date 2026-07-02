# central-deploy Docker Compose Contract

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).

> **Canonical home:
> [`robotsix-central-deploy`](https://github.com/damien-robotsix/robotsix-central-deploy).**
> The contract is implemented by central-deploy's parser and served by the
> running server, so the authoritative copy lives — and versions — with the
> code. This page is a pointer, not a copy; an earlier copy kept here drifted
> from the implementation (gateway routing, § 8 config) and was removed.

## Where to read it

- **Rendered:** <https://robotsix.net/central-deploy/DEPLOY_CONTRACT/>
- **Source:**
  [`docs/DEPLOY_CONTRACT.md`](https://github.com/damien-robotsix/robotsix-central-deploy/blob/main/docs/DEPLOY_CONTRACT.md)
  in the central-deploy repo
- **From the running server:** `GET /help/deploy-contract` on the deploy
  dashboard (the server ships the same file inside its image)

## What it covers

The contract is the authoritative specification for the
`deploy/docker-compose.yml` a service repo must ship before central-deploy's
onboarding flow accepts it:

- the machine-readable version header (`# central-deploy-contract-version: 1`)
  and its breaking-change semantics;
- structural rules — service keys, primary/sibling designation, container
  naming;
- required and optional fields (image, ports, named volumes, environment
  secret slots, healthcheck);
- the `robotsix.deploy.*` extension labels (primary, claude-mount,
  host-docker-sock, config-target, config-assist);
- volume declarations and the stateful-volume onboarding gate;
- ignored vs. prohibited compose fields (error classification);
- runtime configuration via `config/config.yaml` (§ 8) and the
  field → `ComponentConfig` mapping.

For the task-oriented walkthrough of making a repo deployable, see
[Integrating a service](integrating-a-service.md).
