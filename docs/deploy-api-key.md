# Deploy API key provisioning

> **Scope: any component deployed by robotsix-central-deploy that needs to call
> the deploy lifecycle API.** Deploy API key provisioning is **opt-in** — a
> component that does not declare the opt-in below receives no key, and that is
> a valid choice for components with no need to call the deploy API.

## 1. Opt-in mechanism

A component opts into deploy API key provisioning by declaring a
`central_deploy.api_token` field (typed as `pydantic.SecretStr`) in its config
model:

```python
from pydantic import BaseModel, SecretStr


class CentralDeployConfig(BaseModel):
    """Credentials for calling the deploy lifecycle API."""
    url: str = ""
    api_token: SecretStr = SecretStr("")


class MyComponentConfig(BaseModel):
    central_deploy: CentralDeployConfig = CentralDeployConfig()
```

The committed `config/config.schema.json` advertises the field to
`robotsix-central-deploy` — the presence of `central_deploy.api_token` in the
typed schema is the opt-in signal. A component whose schema does not include
this field receives no key; central-deploy skips it.

The field follows the `<name>_url` + `SecretStr` pattern defined in the
[config standard §6](config-standard.md#6-calling-another-service-a-name_url-config-field).

## 2. Injection path

`robotsix-central-deploy` writes the deploy API key into the component's
**config volume** at deploy time. The key is injected directly into
`config/config.json` under the `central_deploy.api_token` key before the
container starts — the same mechanism used for `fleet_auth.auth_hosts`.

- The value is **provisioned by robotsix-central-deploy automatically** —
  components MUST NOT require manual credential paste.
- The component reads the key from its own config file via `load_config`,
  exactly like any other config field — no special env-var discovery path.
- central-deploy validates the merged config document against the component's
  committed `config/config.schema.json` before writing.

## 3. Secret-handling constraints

- The field is typed as `pydantic.SecretStr` — masked on read (`**********`),
  rendered as `writeOnly` / `format: password` in the JSON Schema, per the
  [config standard §3](config-standard.md#3-one-secret-convention).
- The key is injected by central-deploy at deploy time; it is **never
  persisted in clear text** in central-deploy's config store or in any repo.
- `GET /config` masks the value — the actual key is never returned to any
  caller.
- The config file is written with `0600` permissions in a `0700` directory,
  per `robotsix_config.dump_config`.
- The key is a **first-party secret** and follows the config standard's
  one-file rule: it lives in `config/config.json`, never in a compose
  `environment:` slot. The config standard's
  [`environment:` rule](config-standard.md#5-what-environment-is-for) forbids
  first-party secrets in compose `environment:` — one channel for the value
  prevents the "why is this value what it is" ambiguity and keeps the
  component's config surface uniform.

## 4. Lifecycle

- The key is **(re)injected on every deploy and every update**. central-deploy
  writes the current key into the config volume before starting the container
  on every deploy, update, and restart operation.
- **Enabling the opt-in on an already-deployed component requires a
  redeploy/restart** for the key to be picked up. The config file is only
  rewritten when central-deploy starts the container; a component that adds
  the `central_deploy.api_token` field to its schema after initial deployment
  must be redeployed for the key to appear.
- The component reads its config once at startup. A key rotation by
  central-deploy on a running component takes effect on the next restart —
  the component does not need to poll for key changes.

## 5. Capabilities

The deploy API key grants the component the ability to call
`robotsix-central-deploy`'s **deploy lifecycle API** within the component's
permitted scope:

- Read the component's own deployment status, configuration, and metadata.
- Trigger lifecycle operations the component is authorised to perform
  (e.g. self-restart, self-update, log retrieval).
- Enumerate sibling components visible at the component's access level.

The key is **scoped to the component's own identity** — it does not grant
administrative access to central-deploy or cross-component control. The
operations a component may perform with the key are bounded by
central-deploy's per-component authorisation, not by the key itself.

## 6. Relationship to chat access

The [chat access standard](chat-access-standard.md) defines a specific
consumer of this mechanism: when an operator enables chat access for a
component, central-deploy provisions the deploy API key so the chat agent can
call the deploy lifecycle API on behalf of that component. The chat access
standard's §3.1 describes the same `central_deploy.api_token` injection path
documented here.

This page is the **authoritative definition** of the provisioning mechanism;
the chat access standard is a specific use case that consumes it.

## Cross-references

- [Config standard](config-standard.md) — the one-file rule, `SecretStr`
  convention, `<name>_url` pattern, and what `environment:` is for.
- [Config ownership](config-ownership.md) — the boundary between deploy-plane
  and component-owned config.
- [Chat access standard](chat-access-standard.md) — the chat-agent use case
  that consumes this mechanism.
- [Deploy contract](deploy-contract.md) — the `deploy/docker-compose.yml`
  shape.
