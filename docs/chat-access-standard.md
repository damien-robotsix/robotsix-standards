# Chat access standard

> **Scope: any deployable component that wants to be operable by the chat agent
> (robotsix-chat).** Chat access is **opt-in** — a component that does not
> expose the endpoints and labels below is invisible to chat, and that is a
> valid choice for components with no chat-operable surface.

The chat agent (`robotsix-chat`) can invoke operations on fleet components
through a generic `component_request` tool. This page defines what a component
must do to make itself available through that tool — a standard skill endpoint
and a deploy compose label. Components that opt in are listed by the roster
endpoint below, never discovered by scanning.

---

## 1. Skill endpoint (`GET /chat-skill`)

A component that wants chat access serves **`GET /chat-skill`** on its primary
port. The endpoint returns **`text/markdown`** with HTTP 200 in the shape of a
Claude SKILL.md file:

- **YAML frontmatter** (delimited by `---` lines) containing at minimum:

  | Key | Required | Description |
  |---|---|---|
  | `name` | **Yes** | Short kebab-case name for the skill, matching the component id |
  | `description` | **Yes** | One sentence describing what the skill lets the chat agent do |

- **Body** (the Markdown after the closing `---`) covering:

  1. **What the service does** — a concise overview the chat agent reads to
     decide whether this component is relevant to the user's request.
  2. **How to drive its HTTP API** — endpoints the agent may call, request and
     response shapes, error conventions. Enough detail that the agent can form
     correct requests without guessing.
  3. **Safety rules** — an explicit list of operations or data classes that
     **require the chat agent to get explicit user confirmation** before
     proceeding. This is the primary guardrail: the skill author decides which
     operations are safe for the agent to perform unprompted and which need a
     human in the loop.

The endpoint is served by the running container so the skill document always
matches the deployed version. No separate SKILL.md file in the repo is
required — though committing the content as a source-of-truth Markdown file
that the endpoint reads at startup is a reasonable implementation pattern.

### Minimal example

```markdown
---
name: robotsix-mill
description: Manage the robotsix ticket board — create, read, update tickets.
---

## Overview

robotsix-mill is the ticket-board service. It manages work items (tickets)
with states draft → todo → in-progress → done. The chat agent uses it to
create, read, update, and list tickets on behalf of the operator.

## HTTP API

All endpoints are under `/api/v1/`. JSON request and response bodies.

### `GET /api/v1/tickets`
List tickets. Optional query params: `state`, `assignee`.

### `POST /api/v1/tickets`
Create a ticket. Body: `{"title": "...", "body": "..."}`.

### `PATCH /api/v1/tickets/<id>`
Update ticket fields. Body may include `state`, `assignee`, `title`, `body`.

## Safety rules

- **Reading tickets and listing the board** is safe without confirmation.
- **Creating, updating, or closing tickets** requires explicit user
  confirmation — state mutations on the board must not be driven by the
  agent unprompted.
```

---

## 2. Compose label

In the component's `deploy/docker-compose.yml`, add the label on the primary
service:

```yaml
labels:
  robotsix.deploy.chat-access: "true"
```

This label hints the deployer to **default the component's chat-access
checkbox to on** in the central-deploy UI. The operator checkbox
(`robotsix-central-deploy`'s per-component toggle) remains the actual
authorization switch — the label only sets the initial state. An operator can
disable chat access for any component regardless of the label.

---

## 3. Roster, not discovery

The chat agent learns which components it may talk to from
**`robotsix-central-deploy`'s roster endpoint**, never by network scanning or
DNS enumeration:

- **`GET /chat/components`** — returns the list of components whose operator
  has enabled chat access (the per-component checkbox is on). Each entry
  includes the component's base URL and the skill metadata parsed from its
  `/chat-skill` endpoint.
- The chat agent reaches central-deploy via explicit configuration fields:
  `central_deploy.url` (a `str`) and `central_deploy.api_token` (a
  `pydantic.SecretStr`), following the same `<name>_url` + `SecretStr`
  pattern in the [config standard section 5](config-standard.md#6-calling-another-service-a-name_url-config-field).
  No injected addresses, no service discovery — plain config fields are the
  whole mechanism. This standard does not change section 5; it uses the
  existing pattern.

---

## 4. Trust model

The trust model is a direct restatement of the
[component standard](component-standard.md)'s authentication section, applied
to chat operations:

- **The gateway authenticates once.** `robotsix-central-deploy` validates the
  operator's session on every proxied request before traffic reaches a
  component.
- **The internal network is trusted.** Components behind the gateway receive
  only authenticated requests and do not ship per-component auth.
- **The per-component chat-access checkbox is the authorization boundary for
  chat operations.** An operator grants or revokes chat access per component
  in the central-deploy UI. The skill endpoint's safety rules (user
  confirmation for specific operations) are a second layer — the checkbox
  controls whether the agent can reach the component at all; the safety rules
  control what the agent may do once connected.
- **A component must never be exposed directly to an untrusted network** on
  the assumption that it protects itself. Chat access does not change this —
  the skill endpoint is an internal HTTP route behind the gateway, not a
  public API.

---

## Reference

- [Component standard](component-standard.md) — the three deploy modes, auth model,
  health endpoint.
- [Config standard §5](config-standard.md#6-calling-another-service-a-name_url-config-field) —
  the `<name>_url` + `SecretStr` pattern for service-to-service calls.
- [Integrating a service](integrating-a-service.md) — the end-to-end onboarding
  guide (chat-access checklist items).
