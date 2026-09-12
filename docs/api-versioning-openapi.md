# API versioning & OpenAPI schema

> **Scope: deployable components that expose an HTTP API.** A component whose
> only HTTP surface is the mandatory `/health` and `/readyz` endpoints (see the
> [component standard](component-standard.md) and
> [health endpoints](health-endpoints.md)) does not need this — probe endpoints
> carry no versioned contract and no request/response body models. This applies
> *in addition to* the [repo baseline](repo-baseline.md) and
> [component standard](component-standard.md).

Every HTTP API in the fleet exposes its stable contract under a **URL-prefix
version** (`/api/v1/...`) and serves a **machine-readable OpenAPI schema**
describing every route and body model. Header-based versioning
(`Accept`-negotiation, an `X-API-Version` header) and a service that ships no
schema at all are both out — a URL prefix is trivially matched by
nginx/Traefik/Caddy, gives distinct cache keys, is visible in logs without
header parsing, and is debuggable with plain `curl`; an OpenAPI schema makes the
contract discoverable and verifiable instead of something every integration
reverse-engineers from example responses.

Every mature Python ASGI agent/chat server settles on this shape — the
`full-stack-fastapi-template` (`API_V1_STR = "/api/v1"`), LangGraph Platform
(`/api/v1/runs/stream`), vLLM (`/v1/chat/completions`), Langflow (`/api/v1/...`),
and Agenta (`APIRouter(prefix="/v1")`). None of them version by header.

## The rule

### 1. URL-prefix versioning — the app owns `/api/v1`

The stable API is mounted under a version prefix, and the **application owns
that prefix** via a router prefix — never via proxy path stripping that the app
is unaware of.

- **Path shape:** `GET /api/v1/<resource>`. The `v1` segment is the contract
  version; a breaking change ships as `/api/v2/...` alongside `v1`, not as a
  mutated `v1`.
- **Owned in the app, not the proxy:** the prefix comes from the router
  (`APIRouter(prefix=settings.API_V1_STR)` / `app.include_router(..., prefix=...)`),
  so the same paths work whether the service is hit directly, behind the fleet
  edge, or from a test client. A prefix that exists only because the reverse
  proxy rewrites the path is invisible to the app and to its own OpenAPI schema.
- **No header versioning:** the contract version is never selected by an
  `Accept` media-type parameter or an `X-API-Version` request header. Header
  versioning is invisible to path-based routers, splits no cache key, and hides
  the version from logs and `curl`.
- **Unversioned operational paths stay unversioned:** `/health`, `/readyz`, and
  `/openapi.json` / `/docs` are infrastructure, not the versioned contract, and
  keep their fixed top-level paths.

### 2. OpenAPI schema — every route and body model described

The service serves a JSON OpenAPI document describing all request/response body
models and route contracts, plus interactive docs.

- **FastAPI-based services get it automatically.** FastAPI generates
  `/openapi.json` and serves `/docs` out of the box. `docs_url` and
  `openapi_url` must **not** be disabled — the only exception is a surface
  gated behind gateway auth, where the docs are reachable through the
  authenticated edge rather than removed. Pair this with
  [FastAPI Pydantic field descriptions](fastapi-pydantic-field-descriptions.md)
  so the generated schema is self-documenting.
- **Bare-Starlette services must add a schema layer.** Plain `Starlette()` has
  **no** OpenAPI support — it ships neither `/openapi.json` nor `/docs`. A
  Starlette service must add a schema-generation layer (Starlette's own
  `SchemaGenerator`, or a decorator library such as FastOpenAPI) rather than
  shipping with no schema. A service that would otherwise ship plain
  `Starlette()` should prefer FastAPI unless there is a concrete reason not to.
- **The schema is part of the contract:** it describes the versioned routes, so
  its `paths` carry the `/api/v1` prefix the app owns.

### 3. Correct reverse-proxy topology — `servers` matches reality

The OpenAPI `servers` block and the paths a client actually calls must agree,
even when the fleet edge sits in front.

- **Prefer forwarding the full path unchanged** and letting the app own the
  `/api/v1` prefix — the simplest topology, and the one where the generated
  schema is correct with no extra configuration.
- **If the gateway strips a prefix**, set the app's `root_path` (FastAPI/ASGI
  `root_path`, or an explicit `servers` entry) so the OpenAPI `servers` URL
  reflects the externally visible base path. A schema whose `servers`/`paths`
  disagree with the real external URL sends every generated client to a 404.

## FastAPI reference implementation

```python
from fastapi import APIRouter, FastAPI
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_V1_STR: str = "/api/v1"
    # Set when the fleet edge strips the prefix before forwarding; leave "" when
    # the full path is forwarded unchanged (the preferred topology).
    ROOT_PATH: str = ""


settings = Settings()

# docs_url / openapi_url are left at their defaults — never disabled.
app = FastAPI(
    title="example-component",
    root_path=settings.ROOT_PATH,  # so OpenAPI `servers` matches the edge
)

api_v1 = APIRouter(prefix=settings.API_V1_STR)


@api_v1.get("/things/{thing_id}")
async def get_thing(thing_id: str) -> dict[str, str]:
    return {"id": thing_id}


app.include_router(api_v1)


# Operational endpoints stay unversioned (see the health-endpoints standard).
@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

This serves the contract at `/api/v1/things/{thing_id}`, exposes
`/openapi.json` and `/docs` automatically, and — with `ROOT_PATH` set to the
stripped prefix — emits a `servers` entry a generated client can call directly.

## Failure modes this prevents

- **Un-discoverable contracts.** A service that ships no `/openapi.json`
  forces every integration to reverse-engineer request and response shapes from
  example payloads, which drift silently as the code changes. A served schema is
  the single source of truth a client can generate against and a test can assert
  on.
- **Plain-`Starlette()` blind spots.** A bare `Starlette()` app ships zero
  schema and zero docs, and nothing in CI notices — the gap is invisible until a
  consumer needs the contract. Requiring a schema layer closes it fleet-wide.
- **Header-versioning fragility.** With the version in an `Accept` parameter or
  `X-API-Version` header, path routers can't split traffic by version, caches
  collapse every version onto one key, and the version never appears in access
  logs or a `curl` command — making a versioned request indistinguishable from an
  unversioned one at every layer between client and app.
- **Proxy-owned prefixes.** When the `/api/v1` prefix exists only because the
  reverse proxy rewrites the path, the app's own routes, tests, and OpenAPI
  schema all disagree with the external URL — the schema advertises paths the
  edge never serves, and a direct call from a sibling container 404s.
- **Wrong `servers` after prefix stripping.** A gateway that strips the prefix
  without a matching `root_path` yields an OpenAPI document whose `servers`/`paths`
  point at the internal base path, so every client generated from the schema
  targets a URL that returns 404 from outside.
