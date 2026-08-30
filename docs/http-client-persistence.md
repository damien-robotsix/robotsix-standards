# HTTP client persistence and explicit timeouts

> **Scope: every Python repository that makes outbound HTTP calls.** A repo
> whose only HTTP surface is serving inbound requests (a pure FastAPI service
> that never calls another service) is exempt — this only applies when the
> component is itself an HTTP *client*. This applies *in addition to* the
> [repo baseline](repo-baseline.md).

Every fleet component that makes outbound HTTP calls uses a **single
persistent `httpx.Client` (or `requests.Session`) with an explicit
`timeout`**, constructed once and reused for all requests. Module-level
convenience functions (`httpx.get`, `httpx.post`, `requests.get`) that
open a fresh connection per call are forbidden — they bypass connection
pooling and silently inherit library-default timeouts that may not match
the caller's expectations.

## The rule

### 1. One persistent client per process

Construct a single `httpx.Client` (or `requests.Session`) once — at module
level or via dependency injection — and route every outbound HTTP call
through it. Do not use `httpx.get()`, `httpx.post()`, `requests.get()`, or
any other module-level convenience helper that creates an ephemeral client
per call.

```python
# ✅  One persistent client with an explicit timeout
import httpx

_client = httpx.Client(timeout=httpx.Timeout(10.0))


def call_external_api(url: str) -> dict:
    response = _client.get(url)
    response.raise_for_status()
    return response.json()
```

```python
# ❌  Ephemeral per-call helper — fresh connection, no explicit timeout
import httpx

def call_external_api(url: str) -> dict:
    response = httpx.get(url)  # no timeout argument; default 5 s
    response.raise_for_status()
    return response.json()
```

The persistent client holds a connection pool and reuses connections
across calls, avoiding the TCP handshake and TLS negotiation on every
request. The `httpx.Client` and `requests.Session` objects are
thread-safe for read-only use; for async code, prefer an `httpx.AsyncClient`
constructed the same way.

### 2. Explicit timeout — never rely on library defaults

The client MUST carry an explicit `timeout=` value. Do not rely on the
library's built-in default — httpx's default is 5 seconds for
connect/read/write/pool, requests' default is effectively indefinite
(no timeout). Neither default is a safe universal choice: the right
timeout depends on the target service's SLA and the caller's own latency
budget.

```python
# ✅  Explicit timeout
_client = httpx.Client(timeout=httpx.Timeout(10.0))

# ❌  No timeout — library default (httpx: 5 s, requests: indefinite)
_client = httpx.Client()

# ❌  Per-call timeout without a persistent client — still opens a fresh
#     connection per call
httpx.get(url, timeout=10.0)
```

For `requests.Session`, set the timeout on the session and let every
request inherit it:

```python
import requests

_session = requests.Session()
_session.timeout = 10.0  # seconds — applies to every request
```

### 3. Allow the client to be caller-configurable

When a library wraps an HTTP client for fleet-wide reuse (e.g. a GitHub
App auth helper, a shared API client), accept an optional `client` or
`session` parameter rather than hard-coding the client. This lets the
caller control timeouts, transport-level retries, proxy settings, and TLS
configuration without monkey-patching.

```python
# ✅  Caller can supply their own client
from typing import Optional

import httpx


class GitHubAppAuth:
    def __init__(self, client: Optional[httpx.Client] = None):
        self._client = client or httpx.Client(timeout=httpx.Timeout(10.0))

    def get_token(self) -> str:
        response = self._client.post(...)
        ...
```

This is the pattern `githubkit` and `PyGithub` follow: the transport is
built by the caller, and the library rides it.

### 4. Retry policy is caller-side

The persistent client itself does not blind-retry all 4xx/5xx responses.
Retry decisions belong to the caller, who knows the endpoint's idempotency
guarantees and the acceptable latency budget. The one fleet-wide exception
is a **401-on-expiry force-refresh** for auth tokens — the auth layer may
retry exactly once after refreshing its credential, because the token
expiry is a known, expected transient failure.

For connection-level retries (DNS failures, TCP resets, TLS handshake
failures), use httpx's built-in transport retry support:

```python
import httpx

_client = httpx.Client(
    timeout=httpx.Timeout(10.0),
    transport=httpx.HTTPTransport(retries=3),  # connection-level only
)
```

This retries at the transport layer — before the request reaches the
server — and does not retry HTTP error responses (4xx/5xx). It is safe
for all idempotent and non-idempotent requests alike.

### 5. Async clients follow the same pattern

For async code, construct an `httpx.AsyncClient` once — typically at
application startup — and reuse it. Do not use `httpx.AsyncClient()` as a
context manager inside every request handler; that creates and destroys a
client per request, defeating connection pooling.

```python
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI


_client: httpx.AsyncClient


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _client
    _client = httpx.AsyncClient(timeout=httpx.Timeout(10.0))
    yield
    await _client.aclose()


app = FastAPI(lifespan=lifespan)
```

## Failure modes this prevents

- **Silent timeout drift.** `httpx.get(url)` with no `timeout=` argument
  silently uses httpx's default 5-second timeout. A call that works in
  development (fast local services) hangs in production (slower cross-network
  calls). An explicit timeout makes the boundary visible and auditable.
- **Connection exhaustion.** Opening a fresh TCP connection per call — which
  `httpx.get()` and `requests.get()` do — consumes ephemeral ports and
  kernel TCP buffers per request. Under load, the process runs out of ports
  (`EADDRNOTAVAIL`) or hits the kernel's connection-track table limit. A
  persistent client pools connections and reuses them, capping the port
  footprint.
- **TLS handshake overhead.** Every fresh connection pays the full TLS 1.3
  handshake cost (~2–3 round-trips). For a service that makes hundreds of
  outbound calls per second, this is wasted CPU and latency. A persistent
  client amortizes the handshake once per connection.
- **Indefinite hangs (requests).** `requests.get()` with no `timeout=`
  argument can block indefinitely — the default timeout is `None`. A remote
  service that stops responding (but doesn't close the connection) hangs the
  calling thread forever, with no deadline, no abort, and no diagnostic
  until the process is restarted.
- **Cross-service timeout inconsistency.** When every component picks its
  own timeout (or none), an operator chasing a latency regression must know
  the timeout value of every hop in the call chain. Explicit, documented
  timeouts make the chain traceable.
- **Retry storms.** A client that blind-retries all 5xx responses can
  amplify a transient backend overload into a sustained outage — the retries
  add load to an already-struggling service. Caller-side retry decisions
  keep the blast radius small.

## SSRF hardening for URL-fetching tools

For tools that fetch attacker-supplied URLs, the additional SSRF-hardening
requirements in [SSRF-hardened httpx fetchers](ssrf-hardened-fetchers.md) are
also mandatory. Timeouts and connection reuse alone do not prevent a fetcher
from being pointed at internal or cloud-metadata endpoints.
