# HTTP error envelope

> **Scope: deployable components that expose an HTTP API.** A component whose
> only HTTP surface is the mandatory `/health` endpoint (see the
> [component standard](component-standard.md)) does not need this — the
> health check is a binary alive/not-alive signal that carries no error body.
> This applies *in addition to* the [repo baseline](repo-baseline.md) and
> [component standard](component-standard.md).

Every HTTP service in the fleet returns errors through a **single, consistent
JSON envelope** registered via centralized exception handlers — never a mix of
ad-hoc shapes per route or per error kind. A shared envelope means every client
and integration — the chat agent, the deploy dashboard, the mill's own API
calls — parses errors the same way, without branching on the response shape.

## The rule

### 1. One error envelope: RFC 9457 problem+json

All error responses use the **RFC 9457 `application/problem+json`** shape:

| Key | Type | Required | Meaning |
|---|---|---|---|
| `type` | URI string | **Yes** | A URI identifying the problem kind (may be a fixed tag URI like `tag:robotsix,2026:validation-error`). |
| `title` | string | **Yes** | A short, human-readable summary of the problem (stable across instances of the same `type`). |
| `status` | integer | **Yes** | The HTTP status code (mirrors the response status line). |
| `detail` | string | No | A human-readable explanation specific to this *occurrence* — may vary per request. |
| `instance` | URI string | No | A URI identifying the specific occurrence (e.g. `tag:robotsix,2026:req/0193a…`). |

**Extension:** every problem response carries a `correlation_id` field (string)
matching the `X-Correlation-ID` (or `x-correlation-id`) header propagated by
`asgi-correlation-id` through the fleet. This ties every error to the original
request in logs and traces, even when the error is returned to a client that
didn't set the header.

```json
{
  "type": "tag:robotsix,2026:not-found",
  "title": "Resource not found",
  "status": 404,
  "detail": "No ticket with id 0193af04…",
  "instance": "tag:robotsix,2026:req/0193af04…",
  "correlation_id": "abc123-def456"
}
```

FastAPI's default `{"detail": "…"}` shape (even with the experimental
`problem_details=True` flag) is **not acceptable** — it cannot carry an error
code, validation arrays, a correlation id, or a type URI, and enabling it
changes the shape only for `HTTPException`, not for validation errors or
unhandled exceptions.

### 2. Centralized registration — every handler in one place

All error responses come from **a single registration function** called once at
startup. Routes never produce error JSON themselves. The registration covers
every error class the framework can surface:

- **`StarletteHTTPException`** (including FastAPI's `HTTPException`) — mapped to
  an RFC 9457 response with the exception's `status_code` and `detail`.
- **`RequestValidationError`** (FastAPI's validation failure from pydantic) —
  mapped to a **422** problem with `type` indicating a validation error and
  `detail` carrying the structured validation errors (the list of `{loc, msg,
  type}` from pydantic).
- **Domain exceptions** the component defines — mapped to appropriate status
  codes with descriptive `type` URIs.
- **Catch-all `Exception`** — mapped to a **500** problem with a fixed
  `"Internal server error"` title and no `detail` in production (the raw
  exception is logged server-side, never leaked to the client).

In FastAPI/Starlette this is done with `app.add_exception_handler()`:

```python
def register_error_handlers(app: FastAPI) -> None:
    """Register the one error envelope for every error class."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return _problem_response(
            status=exc.status_code,
            title=_http_status_title(exc.status_code),
            detail=str(exc.detail),
            type_uri=f"tag:robotsix,2026:http/{exc.status_code}",
            request=request,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        return _problem_response(
            status=422,
            title="Validation error",
            detail=json.dumps(exc.errors()),
            type_uri="tag:robotsix,2026:validation-error",
            request=request,
        )

    @app.exception_handler(Exception)
    async def catch_all_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")  # log the full traceback server-side
        return _problem_response(
            status=500,
            title="Internal server error",
            detail=None,  # never leak raw exceptions to the client
            type_uri="tag:robotsix,2026:internal-error",
            request=request,
        )
```

The exact shape of the helper (`_problem_response`) is implementation detail —
the fleet's shared libraries may provide one — but every handler must call the
same helper so the envelope is truly uniform.

### 3. Routes never emit ad-hoc error JSON

A route that returns error JSON directly — `return {"error": "bad request"}`,
`raise HTTPException(status_code=400, detail="nope")` and relying on the
default handler — breaks the contract. Every client that has written a parser
for the one envelope now hits a different shape and either crashes or silently
misclassifies the error.

Routes signal errors by **raising an exception** — an `HTTPException`, a domain
exception the centralized handler knows about, or (for unhandled cases) letting
the exception propagate to the catch-all. The centralized handlers produce the
JSON.

### 4. Content-Type: `application/problem+json`

Error responses carry `Content-Type: application/problem+json`. This lets
clients detect the RFC 9457 shape from the response headers without inspecting
the body, and it distinguishes the error stream from the success stream
(`application/json`). The centralized handler sets it on every error response.

## Failure modes this prevents

- **Client-side shape branching.** Without a shared envelope, every client that
  calls more than one service must `if "detail" in body … elif "error" in body
  … elif "message" in body …`. One shape removes that code from every
  integration.
- **Error-code blindness.** A plain `{"detail": "Something went wrong"}` with a
  400 status carries no machine-readable error code. The caller must parse the
  human-readable string or guess from the status code alone. An RFC 9457 `type`
  URI gives every error a stable, parseable identifier.
- **Validation-array loss.** FastAPI's default `RequestValidationError` handler
  returns `{"detail": [{"loc": […], "msg": "…", "type": "…"}]}`, which looks
  like a problem detail but is *not* the same shape as `HTTPException` errors.
  A single envelope normalizes both.
- **Traceability gap.** Without `correlation_id` in the error body, matching a
  client-side error to a server-side log line requires timestamps and guesswork.
  Carrying the correlation id in every error response ties the two together
  directly.
- **Exception leakage.** A catch-all that returns `str(exc)` in production
  leaks stack traces, file paths, and sometimes credentials to the client. The
  centralized catch-all logs the traceback server-side and returns a fixed,
  safe title.
