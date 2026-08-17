# Deploy API key provisioning

> **Superseded.** The deploy API key is **retired**. Components must not ship
> or receive a `central_deploy.api_token`, and robotsix-central-deploy must
> not provision one. The internal container network is trusted; the fleet
> edge is the only authentication gate.

robotsix-central-deploy previously auto-provisioned a `central_deploy.api_token`
into each component's config volume so the component could call the deploy
lifecycle API. That mechanism is removed. Under the
[component standard](component-standard.md), a component-issued token checked
on central-deploy's own routes is a second door, and a caller inside the
trusted internal network does not need one.

The chat agent reaches central-deploy's deploy lifecycle API over the internal
container network (`http://central-deploy:8100`) with **no credential** — see
[chat access standard §3](chat-access-standard.md#3-roster-not-discovery).

## What robotsix-central-deploy must do

- Remove its auth layer (`verify_auth`): answer every internal caller, and
  check no component-issued token on any route.
- Retire `_deploy_credential.py` (the injector) and stop writing
  `central_deploy.api_token` into component config volumes.
- Keep the roster and observability endpoints reachable over the internal
  network, not behind the operator's web-login session.

## Cross-references

- [Config standard](config-standard.md) — the one-file rule, `SecretStr`
  convention, `<name>_url` pattern, and what `environment:` is for.
- [Config ownership](config-ownership.md) — the boundary between deploy-plane
  and component-owned config.
- [Chat access standard](chat-access-standard.md) — how the chat agent reaches
  the deploy plane without a credential.
- [Deploy contract](deploy-contract.md) — the `deploy/docker-compose.yml`
  shape.
- [Component standard](component-standard.md) — why components ship no auth.
