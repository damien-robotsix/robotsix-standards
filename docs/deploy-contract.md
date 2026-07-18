# central-deploy Docker Compose Contract

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).
>
> **Canonical home:
> [`robotsix-central-deploy`](https://github.com/damien-robotsix/robotsix-central-deploy).**
> The contract is implemented by central-deploy's parser and served by the
> running server, so the authoritative copy lives — and versions — with the
> code. This page is a pointer, not a copy; an earlier copy kept here drifted
> from the implementation (gateway routing, § 8 config) and was removed.

## Where to read it

- **Source:**
  [`docs/ui/DEPLOY_CONTRACT.md`](https://github.com/damien-robotsix/robotsix-central-deploy/blob/main/docs/ui/DEPLOY_CONTRACT.md)
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
- volume declarations;
- ignored vs. prohibited compose fields (error classification);
- runtime configuration via the repo's config template (§ 8 —
  `config/config.json` + `config/config.schema.json` per the
  [config standard](config-standard.md)) and the field → `ComponentConfig`
  mapping.

## Volumes only — no host-path bind mounts

Deployed components **never bind-mount host paths**; all persistent or shared
state goes through **named volumes** (declared in the compose, or injected by
central-deploy — e.g. the managed `claude-auth` volume behind the
claude-mount label). Coupling a component to host filesystem layout caused a
real outage (2026-07-03, robotsix-chat: host-uid-dependent credential
readability plus a containerized `~` expansion silently auto-creating empty
root-owned host directories). The **single sanctioned exception** is the
Docker socket, read-only, on a hardened non-primary socket-proxy sibling
(`host-docker-sock` label). central-deploy's own infra mounts are the
deployment system itself ([bootstrap tier](deployment-system.md)), not a
managed component.

Resource limits follow the same shape: compose resource fields are ignored —
central-deploy applies a **default memory limit** to every managed container
(overridable per component in the dashboard), so one leaking service OOMs and
restarts alone instead of taking the host with it.

### Volume ownership (deployer guarantee + component obligation)

Docker's copy-up only fixes named-volume ownership when the image already
contains the mount path. When a component uses a path the image never prepared
(e.g. `/data`, `/home/app/.claude`), freshly created volumes stay root-owned
and the component silently fails every write while reporting healthy — chat
lost all conversations in production (2026-07-04).

**Deployer guarantee.** When the deployment system creates a named volume (first
creation only — existing volume data is **never touched**), it makes the volume
root writable by the component's runtime uid: either the uid declared via
`user:` in the compose service, or the platform-forced uid when no `user:` is
set.

**Component obligation.** Components **MUST NOT** rely on image-side directory
preparation (Dockerfile `mkdir` / `chown`) for volume mount paths, and
**SHOULD** log resolved persistence paths at startup. The startup log line was
the single diagnostic that made the root-owned-volume outage diagnosable in
seconds rather than hours — without it, a component that cannot write its data
directory reports healthy and the failure is invisible.

For the task-oriented walkthrough of making a repo deployable, see
[Integrating a service](integrating-a-service.md).
