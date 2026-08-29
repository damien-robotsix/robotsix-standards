# HTTP security response headers

> **Scope: deployable components that serve HTTP responses** — especially those
> rendering an HTML web UI. This applies *in addition to* the
> [repo baseline](repo-baseline.md) and [component standard](component-standard.md).

Every fleet service that serves HTTP responses emits the standard OWASP security
response headers via a single, shared middleware. Hand-rolling these headers per
service — or leaving them unset — exposes every HTML surface to clickjacking,
MIME-sniffing, and referrer-leak classes of issues. Missing or misconfigured
security response headers are the canonical example of
[OWASP Top 10 A05:2021 — Security Misconfiguration](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/),
which this standard exists to close fleet-wide.

## The rule

### 1. Use the `secure` library with Preset.BALANCED as the baseline

All services use the maintained [`secure`](https://pypi.org/project/secure/)
Python library (≥2.0.1) to set security headers. A hand-rolled
`BaseHTTPMiddleware` is only appropriate for a single custom header; for the
OWASP suite, `secure` handles CSP construction, deduplication, and
normalization.

The default preset is **`Preset.BALANCED`** (importable as `Secure.with_default_headers()`),
which provides a safe, low-friction baseline:

| Header | Value |
|---|---|
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `SAMEORIGIN` (or `DENY` if the service is never framed) |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Content-Security-Policy` | `default-src 'self'` (relax per-app for inline assets) |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (only behind TLS) |

Services that require a stricter posture — e.g. an admin dashboard that must
never be framed and must restrict script sources tightly — use
`Preset.STRICT` instead. Services that need to relax the CSP for inline styles
or scripts do so by calling the `Secure` object's update methods rather than
bypassing the middleware.

### 2. Integration: one middleware, registered once

The `SecureASGIMiddleware` is added to the ASGI app once at startup. Routes
never set security headers themselves — the middleware applies the same set to
every response.

```python
from secure import Secure
from secure.middleware import SecureASGIMiddleware

secure_headers = Secure.with_default_headers()
app.add_middleware(SecureASGIMiddleware, secure=secure_headers)
```

For Starlette/FastAPI apps, this is the standard `app.add_middleware()` call
during application construction. The middleware must be registered before any
route handlers that could return a response.

### 3. CSP relaxation is explicit and auditable

The `default-src 'self'` CSP blocks inline styles and scripts, which some
frontend frameworks require. When a service needs to relax the CSP, it does so
by calling methods on the `Secure` object — e.g.
`secure_headers.csp.default_src = "'self' 'unsafe-inline'"` — rather than
disabling the header or building a CSP string by hand. This keeps every CSP
modification traceable to a single, grep-able location.

### 4. HSTS is conditional on TLS

The `Strict-Transport-Security` header is only emitted when the service is
behind TLS. The `secure` library detects this from the request scheme and
suppresses the header on plain-HTTP requests automatically — the service does
not need to branch on this itself.

## How this is enforced

This standard governs downstream deployable components, not this repo, so there
is no CI gate here that can inspect a component's ASGI app. Enforcement is by
**audit** — checked at component code review and by the periodic
standards-audit agent — against the criteria below. Each criterion maps to one
of the four rules and is verifiable by reading the component's application-setup
module (the same place [`SecureASGIMiddleware`](#2-integration-one-middleware-registered-once)
is registered).

| Rule | Audit criterion |
|---|---|
| 1. `secure` ≥2.0.1 baseline | The component depends on `secure` (≥2.0.1) in its manifest and builds its header object from `Secure.with_default_headers()` (`Preset.BALANCED`) or `Preset.STRICT` — not a hand-rolled `BaseHTTPMiddleware`. |
| 2. One middleware, registered once | Code review verifies the ASGI app calls `app.add_middleware(SecureASGIMiddleware, ...)` exactly once during application construction, and that no route handler sets security headers itself. |
| 3. CSP relaxation is explicit | Every CSP relaxation is a method call on the `Secure`/CSP object at the single registration site — `grep` for `csp` in the app-setup module surfaces all relaxations; a hand-built CSP string or a disabled header is a violation. |
| 4. HSTS conditional on TLS | The service does not branch on the request scheme to set `Strict-Transport-Security` itself; it relies on the `secure` library's automatic TLS detection. |

A component that serves HTTP responses and fails any criterion is
non-compliant; the fix is always the same — register the shared
`SecureASGIMiddleware` at application construction and route every header
change through the `Secure` object.

## Failure modes this prevents

- **Clickjacking.** Without `X-Frame-Options` or CSP `frame-ancestors`, an
  attacker can embed the service's UI in an invisible iframe on a malicious
  page and trick users into clicking UI elements they cannot see.
- **MIME-sniffing attacks.** Without `X-Content-Type-Options: nosniff`, older
  browsers may guess the content type of a response and execute a user-uploaded
  text file as JavaScript if the server's `Content-Type` header is missing or
  wrong.
- **Referrer leakage.** Without `Referrer-Policy`, full URLs — including path
  and query string — leak to third-party sites when a user clicks an external
  link from the service's UI. Query strings often carry tokens, identifiers,
  or search terms.
- **Permission abuse.** Without `Permissions-Policy` denying sensitive APIs
  (`geolocation`, `microphone`, `camera`), any JavaScript running in the
  service's origin — including third-party scripts loaded via CDN — can request
  these permissions without the user's meaningful consent.
- **Downgrade attacks.** Without `Strict-Transport-Security`, a MITM attacker
  can rewrite HTTPS links to HTTP and intercept traffic that the user believes
  is encrypted.
- **Cross-service inconsistency.** Hand-rolling headers per service produces
  slightly different header sets, different header-name casing, and different
  CSP syntax across the fleet. A single middleware — the same library, the same
  preset, the same integration pattern — eliminates per-service drift.
