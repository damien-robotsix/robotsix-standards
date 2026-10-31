# HTTP security response headers

> **Scope: deployable components that serve HTTP responses** — especially those
> rendering an HTML web UI. This applies *in addition to* the
> [repo baseline](repo-baseline.md) and [component standard](component-standard.md).

Every fleet service that serves HTTP responses emits the standard OWASP security
response headers via a single, shared middleware. Hand-rolling these headers per
service — or leaving them unset — exposes every HTML surface to clickjacking,
MIME-sniffing, and referrer-leak classes of issues. Missing or misconfigured
security response headers are the canonical example of
[OWASP Top 10 A02:2025 — Security Misconfiguration](https://owasp.org/Top10/2025/A02_2025-Security_Misconfiguration/),
which this standard exists to close fleet-wide.

## The rule

### 1. Use the `secure` library with Preset.BALANCED as the baseline

All services use the maintained [`secure`](https://pypi.org/project/secure/)
Python library (≥2.0.1) to set security headers. A hand-rolled
`BaseHTTPMiddleware` is only appropriate for a single custom header; for the
OWASP suite, `secure` handles CSP construction, deduplication, and
normalization.

The default preset is **`Preset.BALANCED`** (importable as `Secure.with_default_headers()`),
which provides a safe, low-friction baseline. The table below is exactly what
`secure` 2.0.1's BALANCED emits — the upstream definition is
[`preset_kwargs()` in `secure/_internal/presets.py`](https://github.com/TypeError/secure/blob/main/secure/_internal/presets.py),
and it wins if the two ever disagree. The **Fleet** column names the only rows
the fleet changes on top of the preset:

| Header | BALANCED value | Fleet |
|---|---|---|
| `Cross-Origin-Opener-Policy` | `same-origin` | as preset |
| `Cross-Origin-Resource-Policy` | `same-origin` | as preset |
| `Content-Security-Policy` | `default-src 'self'; base-uri 'self'; font-src 'self' https: data:; form-action 'self'; frame-ancestors 'self'; img-src 'self' data:; object-src 'none'; script-src 'self'; script-src-attr 'none'; style-src 'self' https: 'unsafe-inline'; upgrade-insecure-requests` | as preset; relaxations only per [rule 3](#3-csp-relaxation-is-explicit-and-auditable) |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` | as preset (effective only over TLS; ignored by browsers on HTTP — see [rule 4](#4-hsts-is-emitted-unconditionally-and-takes-effect-over-tls)) |
| `Permissions-Policy` | `geolocation=(), microphone=(), camera=()` | as preset |
| `Referrer-Policy` | `strict-origin-when-cross-origin` | as preset |
| `Server` | empty value (overwrites the server banner) | as preset |
| `X-Content-Type-Options` | `nosniff` | as preset |
| `X-Frame-Options` | `SAMEORIGIN` | `DENY` allowed if the service is never framed |
| `Cache-Control` | *not emitted* | **added:** `no-store, max-age=0` — see [rule 5](#5-sensitive-responses-are-not-stored) |

Note that the BALANCED CSP already allows inline styles (`'unsafe-inline'` in
`style-src`), `https:`/`data:` fonts and `data:` images; it does **not** allow
inline scripts. Audit a component's CSP against this value, not against a bare
`default-src 'self'`.

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

The BALANCED CSP blocks inline scripts (`script-src 'self'`,
`script-src-attr 'none'`) and limits other sources to the values in the
[rule 1 table](#1-use-the-secure-library-with-presetbalanced-as-the-baseline),
which some frontend frameworks need loosened. When a service needs to relax the CSP, it does so
by calling methods on the `Secure` object — e.g.
`secure_headers.csp.default_src = "'self' 'unsafe-inline'"` — rather than
disabling the header or building a CSP string by hand. This keeps every CSP
modification traceable to a single, grep-able location.

### 4. HSTS is emitted unconditionally and takes effect over TLS

The `secure` library does **not** inspect the request scheme: the
`SecureASGIMiddleware` applies every configured header — including
`Strict-Transport-Security` — to every HTTP response, plain HTTP included.
This is harmless: user agents MUST ignore an HSTS header received over
non-secure transport ([RFC 6797 §8.1](https://www.rfc-editor.org/rfc/rfc6797#section-8.1)),
and fleet services sit behind a TLS-terminating edge, so the header takes
effect only on the TLS hop from the edge to the browser. Services MUST NOT
strip `Strict-Transport-Security` or branch on the request scheme to suppress
it, and the edge MUST pass it through on HTTPS responses. The HSTS policy
must carry `max-age` of at least one year (`31536000`), per
[OWASP ASVS 5.0 V3.4.1](https://owasp.org/www-project-application-security-verification-standard/)
and the [OWASP HTTP Strict Transport Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/HTTP_Strict_Transport_Security_Cheat_Sheet.html);
the BALANCED default qualifies.

*Failure mode this prevents:* an auditor or agent assumes the library gates
HSTS by scheme, and a service or edge change that drops HSTS on the HTTPS path
goes unnoticed.

### 5. Sensitive responses are not stored

Every response that is authenticated or personalised, or that carries config,
conversation (chat transcripts, LLM output) or credential-adjacent data, MUST
carry `Cache-Control: no-store`, per
[OWASP ASVS 5.0 V14.3.2](https://owasp.org/www-project-application-security-verification-standard/)
("sufficient anti-caching HTTP response header fields (i.e.,
`Cache-Control: no-store`)"). BALANCED emits **no** `Cache-Control` header, so
following rules 1–2 alone leaves these responses to the browser's heuristic
caching. `no-cache` does not satisfy this rule: it permits storing the response
and only requires revalidation before reuse
([RFC 9111 §5.2.2.4](https://www.rfc-editor.org/rfc/rfc9111#section-5.2.2.4));
only `no-store` forbids storage
([RFC 9111 §5.2.2.5](https://www.rfc-editor.org/rfc/rfc9111#section-5.2.2.5)).

The simplest compliant setup — and the fleet default — adds the header to the
same `Secure` object at the single registration site, so every response
carries it:

```python
from secure import CacheControl, Secure
from secure.middleware import SecureASGIMiddleware

secure_headers = Secure.with_default_headers()
secure_headers.headers_list.append(CacheControl().no_store().max_age(0))
app.add_middleware(SecureASGIMiddleware, secure=secure_headers)
```

**Opt-out for static public assets is explicit.** `SecureASGIMiddleware`
*overwrites* any `Cache-Control` a route sets, so a hashed `/static/` file
cannot opt out by setting its own header on the response. A public,
non-personalised asset path (e.g. content-hashed files under `/static/` with a
long `max-age`) opts out in one of two ways, both applied at the app-setup site:

1. **Serve the assets from the edge**, outside the component, so the component
   never emits a `Cache-Control` for them. This is the preferred option.
2. **Add a path-scoped ASGI middleware** that rewrites the `Cache-Control`
   header on `http.response.start` messages for requests whose path starts with
   the asset prefix (e.g. `/static/`). Register it with `app.add_middleware(...)`
   *after* `SecureASGIMiddleware` so it is the outer layer: Starlette makes the
   last-added middleware outermost, so its send wrapper sees the headers after
   `SecureASGIMiddleware` has written its own. The middleware must match the
   asset prefix only; it must never match an API or HTML route.

That override is the only place a non-`no-store` `Cache-Control` is set. Never
relax the default for an API or HTML route.

*Failure mode this prevents:* a chat transcript, LLM answer, config view or
deploy-dashboard response is written to the browser's disk cache, survives
logout, and is readable later by anyone with access to a shared or
compromised machine.

## How this is enforced

This standard governs downstream deployable components, not this repo, so there
is no CI gate here that can inspect a component's ASGI app. Enforcement is by
**audit** — checked at component code review and by the periodic
[`component-security-audit`](mill-agents.md#component-security-audit) agent — against the criteria below. Each criterion maps to one
of the five rules and is verifiable by reading the component's application-setup
module (the same place [`SecureASGIMiddleware`](#2-integration-one-middleware-registered-once)
is registered).

| Rule | Audit criterion |
|---|---|
| 1. `secure` ≥2.0.1 baseline | The component depends on `secure` (≥2.0.1) in its manifest and builds its header object from `Secure.with_default_headers()` (`Preset.BALANCED`) or `Preset.STRICT` — not a hand-rolled `BaseHTTPMiddleware`. |
| 2. One middleware, registered once | Code review verifies the ASGI app calls `app.add_middleware(SecureASGIMiddleware, ...)` exactly once during application construction, and that no route handler sets security headers itself. |
| 3. CSP relaxation is explicit | Every CSP relaxation is a method call on the `Secure`/CSP object at the single registration site — `grep` for `csp` in the app-setup module surfaces all relaxations; a hand-built CSP string or a disabled header is a violation. |
| 4. HSTS emitted, effective over TLS | The configured `Secure` object includes `StrictTransportSecurity` with `max-age` ≥ `31536000` (the BALANCED default qualifies), and no code strips the header or branches on the request scheme to suppress it. Optionally, a deploy smoke check runs `curl -sI https://<host>/health` and asserts a `strict-transport-security` header is present. |
| 5. Sensitive responses are not stored | The configured `Secure` object includes `CacheControl().no_store()` so every authenticated, personalised, config, conversation or credential-adjacent response carries `Cache-Control: no-store`. `grep` for `Cache-Control`/`CacheControl` in the app-setup module surfaces every opt-out; any opt-out that covers a non-public path, or any `no-cache`-only value on such a response, is a violation. Optionally, a deploy smoke check runs `curl -sI` against an authenticated route and asserts `cache-control` contains `no-store`. |

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
- **Sensitive data left in the browser cache.** Without
  `Cache-Control: no-store`, authenticated JSON and HTML — chat transcripts,
  LLM output, config views — are stored on disk by the browser and stay
  readable after logout on a shared or compromised machine.
- **Audit drift from the real preset.** A header table that does not match
  what BALANCED emits makes auditors judge components against a CSP and a
  header set the fleet never ships.
- **Cross-service inconsistency.** Hand-rolling headers per service produces
  slightly different header sets, different header-name casing, and different
  CSP syntax across the fleet. A single middleware — the same library, the same
  preset, the same integration pattern — eliminates per-service drift.
