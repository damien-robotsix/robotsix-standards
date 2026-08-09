# Health endpoints

> **Scope: deployable components that expose an HTTP API.** Every deployable
> component already serves `GET /health` (per the
> [component standard](component-standard.md)). This page codifies the
> **split** into two distinct endpoints — liveness vs. readiness — that the
> component standard's health section already tees up. This applies *in
> addition to* the [repo baseline](repo-baseline.md) and
> [component standard](component-standard.md).

Every HTTP service in the fleet exposes two health endpoints with different
semantics, following the Kubernetes liveness/readiness probe convention. A
single static `/health` that returns 200 unconditionally reports healthy even
when the backing store is down — masking an outage behind a green probe. Two
endpoints with different contracts let the orchestrator restart dead processes
while also gating traffic away from processes that are alive but can't serve.

## The rule

### 1. Liveness: `/health` — static, no I/O, always 200 while up

The liveness endpoint signals that the **process event loop is running**.
It must return 200 as long as the process is alive, and it must **never**
touch an external dependency — no database query, no downstream HTTP call,
no filesystem stat on a network mount. A database blip must not trigger a
restart cascade.

- **Path:** `GET /health` (the existing fleet path; no new path needed).
- **Contract:** always returns `{"status": "ok"}` with HTTP 200 while the
  process is alive.
- **No dependency I/O:** the handler body is synchronous or a no-op async
  function — it returns immediately without awaiting anything.
- **Auth-exempt:** neither the fleet edge nor the component applies
  authentication to this endpoint, so container healthchecks, the
  orchestrator, and external uptime monitoring can probe it without
  credentials. The edge gives every component a dedicated highest-priority
  `/health` route carrying no auth middleware.

### 2. Readiness: `/readyz` — dependency probe, 503 when degraded

The readiness endpoint signals that the component can **actually serve
traffic**. It runs a lightweight probe of every critical dependency —
datastore, downstream API, message broker — within a short timeout. If all
dependencies respond, it returns 200; if any is unreachable, it returns 503
with a per-dependency status map so the operator can see *which* dependency
is down without tailing logs.

- **Path:** `GET /readyz`.
- **Success (200):** `{"status": "ready"}` when all probed dependencies
  respond within the timeout.
- **Degraded (503):** `{"status": "not ready", "dependencies": {"<name>":
  "up|down|timeout", …}}` when any dependency fails or times out. The
  `dependencies` map names every probed dependency and its status so a
  dashboard or operator can diagnose the failure from the response alone.
- **Timeout:** each individual probe has a short timeout (≤ 2 seconds per
  dependency), and the whole handler returns within 5 seconds — a hung
  readiness probe that blocks the event loop is worse than no probe.
- **Auth-exempt:** same as liveness — no authentication, so the orchestrator
  and load-balancer can probe it.

### 3. What counts as a dependency

Only **critical** dependencies — those whose absence makes the component
unable to serve its primary function. A component that calls three downstream
APIs but can still serve 90% of its endpoints with two of them down should
probe all three and report the degraded one but still return 200 (or use the
dependency map to inform a dashboard without gating traffic). The readiness
check gates *traffic routing*, not logging — err on the side of keeping the
component in rotation unless it is genuinely unable to serve.

Dependencies that are **not** probed at readiness time:

- Sibling containers (the component already starts without them per
  [sibling resilience](component-standard.md#sibling-resilience)).
- Optional integrations that degrade gracefully (e.g. an analytics sink
  whose failures are logged and ignored).
- The deployment system's own infrastructure (gateway, config provider) — if
  those are down the probe request wouldn't reach the component anyway.

### 4. Both endpoints unauthenticated and documented

The deploy README (`deploy/README.md`) documents both endpoints — paths,
expected responses, and probe semantics — so the operator configuring
healthchecks in the orchestrator doesn't have to read source code.

## FastAPI reference implementation

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/health")
async def health() -> dict[str, str]:
    """Liveness: static, no I/O."""
    return {"status": "ok"}


@app.get("/readyz")
async def readyz(request: Request) -> JSONResponse:
    """Readiness: probe critical dependencies."""
    # Each probe has its own timeout; the handler returns within 5 seconds.
    db_ok = await check_database(timeout=2.0)
    api_ok = await check_downstream_api(timeout=2.0)

    all_ok = db_ok and api_ok
    status_code = 200 if all_ok else 503
    return JSONResponse(
        content={
            "status": "ready" if all_ok else "not ready",
            "dependencies": {
                "database": "up" if db_ok else "down",
                "downstream_api": "up" if api_ok else "down",
            },
        },
        status_code=status_code,
    )
```

The probe helpers (`check_database`, `check_downstream_api`) are
implementation detail — a `SELECT 1`, a `GET /health` on the downstream, a
Redis `PING` — but each must respect its timeout and never raise an unhandled
exception (catch, log, and report "down").

## Failure modes this prevents

- **Masked outages.** A single static `/health` returns 200 while the
  database is unreachable. The orchestrator sees a green probe and keeps
  routing traffic to a component that 500s every real request. The readiness
  endpoint catches this and pulls the component from rotation until the
  dependency recovers.
- **Restart cascades.** If the liveness probe touches the database and the
  database blips, every replica restarts simultaneously — turning a brief
  dependency hiccup into a full service outage while all replicas cycle.
  Static liveness means the orchestrator only restarts a process that is
  genuinely stuck.
- **Inconsistent probe paths across repos.** Without a codified split, each
  repo invents its own probe convention — `/healthz`, `/health/live`,
  `/ready`, `/status` — and the operator must configure healthchecks
  differently per service. Two fleet-wide paths remove that configuration
  drift.
- **Undiagnosable readiness failures.** A readiness endpoint that returns a
  bare 503 tells the operator *that* the component is degraded but not
  *why*. The per-dependency status map in the response body means a single
  `curl` from the operator's terminal identifies the failing dependency
  without log access.
