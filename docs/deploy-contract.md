# Deploy contract

The `deploy/docker-compose.yml` shape that the central-deploy system consumes.

> **Canonical source.** The full field-by-field contract lives in
> `robotsix-central-deploy/docs/DEPLOY_CONTRACT.md` (Version 1) and is the
> authoritative reference — central-deploy's own parser implements it. This page
> summarizes it for stack integrators and records one correction. When the two
> disagree, the central-deploy document wins **except** on the `command:` point
> below, which the central-deploy doc currently states incorrectly (fix filed).

## Summary

- **File location:** `deploy/docker-compose.yml` in the service repo. The repo
  root `docker-compose.yml` is the dev compose and is **ignored** by
  central-deploy.
- **Version header (required, first line):** `# central-deploy-contract-version: 1`.
  Missing or unknown version is a parse error.
- **No build.** central-deploy pulls the pre-built `image:` verbatim; a `build:`
  key is a parse error.
- **Primary service.** One service is implicitly primary; with two or more,
  exactly one must carry `robotsix.deploy.primary: "true"`.
- **Named volumes only.** Host bind-mounts are rejected except via the
  `claude-mount` / `host-docker-sock` labels. Every named volume used must be
  declared in the top-level `volumes:`.
- **Secret slots.** An `environment:` key with an empty value is an operator-
  filled secret; a non-empty value is an editable default.
- **Config file injection.** If the repo has `config/config.yaml`, the primary
  service needs `robotsix.deploy.config-target: <in-container path>`, whose
  dirname matches a named-volume mount; central-deploy writes the merged config
  into that volume before start.
- **Stateful volumes.** Flag persistent volumes with
  `robotsix.deploy.stateful: "true"` to get the blocking "starts EMPTY — migrate
  data" onboarding warning.

## Correction: `command:` / `entrypoint:` ARE applied

The central-deploy contract doc (§7) currently says `command:` and `entrypoint:`
are "silently ignored… image CMD/entrypoint is used as-is." **This is wrong vs.
the code** — central-deploy's parser stores `command` and its backend applies it
to primary and sibling containers. Services depend on this: an ENTRYPOINT-only
image with no default `CMD` (e.g. `robotsix-auto-mail`) sets `command:` on each
service to select the subcommand. **Set `command:` when your image needs a
subcommand to start.** (A fix to the central-deploy doc is filed.)

## Config template ties into the config standard

Because `config/config.yaml` is generated from the service's config schema (see
the [config standard](config-standard.md) — `emit_deploy_template`), the deploy
template and the runtime schema never drift. Secret leaves render as empty
strings, which is exactly the central-deploy secret-slot convention.

## Full reference & examples

See `robotsix-central-deploy/docs/DEPLOY_CONTRACT.md` for the complete field
rules, the error-classification table, the `ComponentConfig` mapping, the
extension labels (`claude-mount`, `host-docker-sock`, `config-assist`), and
annotated examples. The [integration guide](integrating-a-service.md) is the
task-oriented walkthrough.
