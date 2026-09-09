# CORS policy

> **Scope: deployable components serving HTTP** — especially those consumed by a
> browser. This applies *in addition to* the [repo baseline](repo-baseline.md)
> and [component standard](component-standard.md).

Fleet components are reached same-origin through the edge domain, and
cross-site request forgery is already closed at that edge (the `SameSite=Lax`
tinyauth session cookie). A component that silently adds a permissive
Cross-Origin Resource Sharing (CORS) middleware — `Access-Control-Allow-Origin: *`,
blind origin reflection, or `Access-Control-Allow-Credentials: true` on a
reflected origin — re-opens the exact cross-site request channel that stance
closed. Missing or misconfigured CORS is a case of
[OWASP Top 10 A02:2025 — Security Misconfiguration](https://owasp.org/Top10/A02_2025-Security_Misconfiguration/),
which this standard exists to close fleet-wide. Absence of a stated policy reads
as "anything goes"; this page states the policy so it does not.

## The rule

### 1. Default posture: no CORS headers at all

Fleet components are consumed same-origin through the edge domain. A component
that serves no cross-origin browser client **MUST NOT** register a CORS
middleware or emit any `Access-Control-*` header. Absence is the secure default
— the browser's same-origin policy does the work, and there is nothing to
misconfigure. A component adds CORS only when it has a concrete, declared
cross-origin need (rule 3); until then, the correct number of CORS headers is
zero.

### 2. Wildcard and reflection are disallowed on authenticated surfaces

`Access-Control-Allow-Origin: *` and blind reflection of the request `Origin`
header are prohibited. `Access-Control-Allow-Credentials: true` **MUST NEVER**
be combined with a wildcard or a reflected origin.

The fleet's CSRF protection is the `SameSite=Lax` tinyauth session cookie set at
the edge — the [component standard](component-standard.md#csrf-is-handled-at-the-fleet-edge-components-ship-none)
states that "Cross-site request forgery (CSRF) is an **edge concern**," handled
once for the whole fleet so that cross-site requests do not carry the cookie and
fail edge authentication before they reach any component. A credentialed
permissive CORS policy re-opens exactly the cross-site request channel that
stance closed: a hostile third-party page can now make the browser send the
authenticated request and *read the response*, which `SameSite=Lax` alone would
have blocked. Wildcard-plus-credentials is not merely discouraged — browsers
reject the combination — but a reflected origin with credentials achieves the
same breach while passing the browser's check, so both are banned.

### 3. Genuine cross-origin need is an explicit, declared exception

A component that must serve cross-origin browsers declares the need explicitly:

- A **static allowlist of exact origins** — full scheme-host-port strings, no
  regex, no suffix or substring matching — in its config model, per the
  [config standard](config-standard.md).
- The **framework's standard middleware** (e.g. Starlette/FastAPI
  `CORSMiddleware`) — no hand-rolled `Access-Control-*` header code, mirroring
  the "single shared `secure` middleware" pattern of
  [HTTP security headers](http-security-headers.md).
- `allow_methods` and `allow_headers` **restricted to what the client actually
  needs** — not `*`.
- The **justification recorded in the component's `AGENT.md`** — the same
  declared-deviation discipline the fleet applies to a lint suppression or a
  hand-rolled auth gate.

An allowlisted, non-wildcard origin MAY use `allow_credentials=true` when the
cross-origin client genuinely needs the session cookie; the allowlist is what
makes that safe.

### 4. Preflight follows the same allowlist

Preflight (`OPTIONS`) responses follow the same static allowlist as actual
requests — a preflight **MUST NOT** be satisfiable by a wildcard. A bounded
`Access-Control-Max-Age` (e.g. `600` seconds) is acceptable to cut preflight
chatter; an unbounded or very long max-age is not, because it delays the effect
of tightening the allowlist.

## How this is enforced

This standard governs downstream deployable components, not this repo, so there
is no CI gate here that can inspect a component's ASGI app. Enforcement is by
**audit** — advisory for now, with no new script added by this standard —
checked at component code review and by the periodic standards-audit agent. The
fleet sweep greps each component for `CORSMiddleware` and
`Access-Control-Allow-Origin`. Any hit must match rule 3: a static allowlist of
exact origins wired through the framework's standard middleware, with the
justification recorded in the component's `AGENT.md`. A hit that uses a
wildcard, reflects the request origin, combines credentials with either, or
carries no `AGENT.md` justification is a finding. No hit at all is the expected,
compliant state (rule 1).

## Failure modes this prevents

- **Silent CSRF-stance bypass.** A credentialed wildcard or reflected-origin
  CORS policy re-opens the cross-site request channel that the edge's
  `SameSite=Lax` cookie closed, letting a hostile page read authenticated
  responses.
- **Origin-reflection exfiltration.** Blind reflection of the request `Origin`
  turns every attacker-controlled page into an allowed origin, exfiltrating
  tokens or data from the authenticated surface.
- **Per-service header drift.** Hand-rolled `Access-Control-*` headers produce
  slightly different, inconsistent policies across the fleet — the same drift
  the shared-middleware pattern exists to eliminate.
- **Undocumented cross-origin surfaces.** A CORS allowance added without an
  `AGENT.md` justification is invisible to review and audit, so nobody can tell
  whether the cross-origin need is real or a copy-pasted default.
