# SSE response headers

> **Scope: deployable components that emit `text/event-stream` (Server-Sent
> Events) responses.** This applies *in addition to* the
> [repo baseline](repo-baseline.md) and [component standard](component-standard.md),
> and complements the [HTTP error envelope](http-error-envelope.md) and
> [HTTP security headers](http-security-headers.md) standards.

Every `text/event-stream` response a fleet service emits carries three
proxy-safety headers: `Cache-Control: no-cache`, `Connection: keep-alive`, and
`X-Accel-Buffering: no`. A hand-rolled
`StreamingResponse(media_type="text/event-stream")` — the pattern a service
uses when it needs a manual heartbeat plus a `request.is_disconnected()` loop —
silently loses these headers unless they are added explicitly, and the first
symptom is usually production-only: events accumulating in a reverse proxy's
buffer while clients wait. A missing or misconfigured proxy-safety header on a
streaming response is a
[Security Misconfiguration (OWASP Top 10 A05:2021)](https://owasp.org/Top10/A05_2021-Security_Misconfiguration/);
the `Cache-Control` and `Connection` header semantics this standard relies on
are defined by [RFC 9110 — HTTP Semantics](https://www.rfc-editor.org/rfc/rfc9110).

## The rule

### 1. Every `text/event-stream` response carries the three headers

| Header | Value | Purpose |
|---|---|---|
| `Cache-Control` | `no-cache` | Prevents caching intermediaries from holding the stream — any stored copy must be revalidated before reuse, so a stale snapshot is never re-served. |
| `Connection` | `keep-alive` | Keeps the connection open for continuous event delivery instead of tearing it down after the first response segment. |
| `X-Accel-Buffering` | `no` | Disables nginx response buffering for this response as a per-response override, with no proxy config change required. With nginx's default `proxy_buffering on`, events otherwise accumulate in the proxy buffer — defeating heartbeats and delaying token delivery until the buffer fills or the connection closes. |

`sse-starlette`'s `EventSourceResponse` — the de-facto standard SSE response
for Starlette/FastAPI — applies this set by default: `Connection: keep-alive`
and `X-Accel-Buffering: no`, plus `Cache-Control: no-store` (a strictly
stronger cache-busting directive than `no-cache`, and acceptable under this
rule). Services that hand-roll their streaming response lose these defaults
and must add the headers explicitly.

### 2. One shared helper — the header set cannot drift per-endpoint

Prefer a single shared `sse_response(...)` factory so the header set is
defined once and cannot drift between endpoints:

```python
from starlette.responses import StreamingResponse


def sse_response(generator, **kwargs) -> StreamingResponse:
    """A StreamingResponse with the mandatory SSE proxy-safety headers."""
    headers = kwargs.pop("headers", {})
    headers.update(
        {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )
    return StreamingResponse(
        generator, media_type="text/event-stream", headers=headers, **kwargs
    )
```

Every SSE endpoint in the service returns `sse_response(...)` — never a bare
`StreamingResponse(media_type="text/event-stream")`. Using
`sse-starlette`'s `EventSourceResponse` instead of a hand-rolled helper is
equally acceptable: its default header set provides the same guarantee from a
single definition point.

### 3. Hand-rolled streaming loops set the headers explicitly

Services that hand-roll the streaming loop — for a manual heartbeat and a
`request.is_disconnected()` check — keep that loop; it is not in tension with
this standard. What the standard forbids is a hand-rolled
`StreamingResponse` that goes out with the default header set: the three
headers are added at the response boundary (the `sse_response` factory), not
inside the generator.

## How this is enforced

This standard governs downstream deployable components, not this repo, so there
is no CI gate here that can inspect a component's SSE endpoints. Enforcement is
by **audit** — checked at component code review and by the periodic
standards-audit agent — against the criteria below. Each criterion maps to one
of the three rules and is verifiable by reading the component's response module:
`grep` for `text/event-stream` and `StreamingResponse` surfaces every SSE
response the component emits.

| Rule | Audit criterion |
|---|---|
| 1. Three headers on every stream | Every `text/event-stream` response carries `Cache-Control` (`no-cache` or the stronger `no-store`), `Connection: keep-alive`, and `X-Accel-Buffering: no`. A hand-rolled `StreamingResponse(media_type="text/event-stream")` that goes out with the default header set is a violation. |
| 2. One shared helper | The header set is defined once — a single `sse_response(...)` factory or `sse-starlette`'s `EventSourceResponse` — and every SSE endpoint routes through it. A `grep` for `text/event-stream` that returns more than one header-setting site (each with its own literal header dict) is a violation. |
| 3. Hand-rolled loops set headers explicitly | Where a component hand-rolls the streaming loop (manual heartbeat plus `request.is_disconnected()`), the three headers are added at the response boundary — the `sse_response` factory — not omitted because the loop is custom. |

A component that emits `text/event-stream` responses and fails any criterion is
non-compliant; the fix is always the same — route every SSE response through the
single shared helper (or `EventSourceResponse`) so the correct header set is the
default for every endpoint.

## Failure modes this prevents

- **Proxy-buffering stalls.** nginx buffers responses by default. Without
  `X-Accel-Buffering: no`, events accumulate in the proxy buffer and are
  flushed only when the buffer fills or the stream ends — heartbeats stop
  reaching clients, and token-by-token delivery degrades into burst delivery.
- **Held streams.** Without a cache-busting `Cache-Control` directive, a
  caching intermediary may hold the unbounded, never-completing stream and
  re-serve a stale snapshot to later clients instead of passing the live
  stream through.
- **Mid-stream connection teardown.** Without `Connection: keep-alive`, an
  intermediary that honors `Connection: close` semantics tears the stream
  down after the first response segment, breaking long-lived event delivery.
- **Per-endpoint header drift.** When each route sets its own headers, the
  first endpoint to skip them (or to use a different directive) reintroduces
  the buffering failure in production. One shared helper — or
  `EventSourceResponse` — makes the correct header set the default for every
  SSE endpoint in the service.
