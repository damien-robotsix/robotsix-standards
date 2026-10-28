# Logging

> **Scope: every deployable component that emits logs while serving requests.**
> Libraries MAY adopt the structlog conventions described here but are not
> required to — they follow the lighter-weight [library internal logging](library-logging.md)
> standard instead. This applies *in addition to* the [repo baseline](repo-baseline.md)
> and [component standard](component-standard.md).

Every deployable service in the fleet emits **structured JSON logs to stdout**
through a single `structlog` pipeline that covers both application code and
framework access logs. A shared convention means every log event is parseable
by the same aggregator query, every request carries a `correlation_id` that
ties error responses (per the [HTTP error envelope](http-error-envelope.md)
standard) to their server-side log lines, and operators never hunt through
mixed plain-text and JSON streams trying to reconstruct a request's lifecycle.

## The rules

### 1. Structured JSON via structlog

Every log record is a single JSON line emitted through `structlog`. The
application configures `structlog.stdlib.ProcessorFormatter` so that both
structlog-native calls AND third-party stdlib-logging calls (including
uvicorn's access log) render through the same JSON pipeline.

```python
import structlog
import logging
from structlog.stdlib import ProcessorFormatter

# structlog processors — the chain that builds each event
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.dev.set_exc_info,
        structlog.processors.format_exc_info,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

# The formatter that produces JSON from the processed event dict
formatter = ProcessorFormatter(
    processor=structlog.processors.JSONRenderer(),
    # The foreign_pre_chain is applied to stdlib-logging records BEFORE
    # they enter the structlog processor chain — it extracts the event
    # dict that the JSON renderer expects.
    foreign_pre_chain=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
    ],
)

# Attach to the root handler — covers uvicorn, sqlalchemy, and any other
# library that uses stdlib logging
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.basicConfig(handlers=[handler], level=logging.INFO)
```

**Accepted simpler alternative: `python-json-logger`.** Repos that do not
need structlog's context-binding and processor chain may use
[`python-json-logger`](https://pypi.org/project/python-json-logger/) as a
drop-in stdlib-logging formatter. The output is still structured JSON to
stdout; the trade-off is no `structlog.contextvars` binding for per-request
context.

**Failure prevented:** mixed ad-hoc `print()` calls and plain-text
`logging.Formatter` output that the aggregator cannot parse. A stream of
`"Fetching /api/foo … done"` lines carries no machine-readable fields —
filtering by level, service, or request id requires regex guesswork that
breaks on the next log-format change.

### 2. JSON to stdout, never a direct shipper

The application appends structured JSON events to stdout via a
`StreamHandler`. It never calls Elasticsearch, Loki, CloudWatch, or any
other log aggregator directly. The orchestration and log-shipper layer
(Docker's json-file driver, journald, or a sidecar collector) owns the
transport.

**Why this matters:** a component that opens a socket to Loki hard-codes
an assumption about the fleet's observability stack. When the operator
switches aggregators or adds a new pipeline stage (enrichment, sampling,
archival), every component must be updated in lockstep. stdout is the
universal interface — every container runtime captures it, and the
shipper configuration lives in one place (the host or the compose file),
not in N application codebases.

The `correlation_id` (and `request_id`) bound to every event by the
middleware (rule 4) is what enables cross-service tracing at the
aggregator: the shipper doesn't need to understand the application —
it just forwards JSON, and the aggregator joins on the correlation id.

**Failure prevented:** per-component aggregator dependencies that turn a
shipper migration into an all-hands fleet change; a component that ships
to Loki when the fleet has standardized on a different backend, producing
a silent log gap.

### 3. Log-level convention

- **Production default is `INFO`** at the root logger. The fleet's
  production config sets `log_level = "INFO"` in every component's config
  model (per the [component standard](component-standard.md#logging)).
- **DEBUG is gated behind config, never a hard-coded default.** No
  `logging.basicConfig(level=logging.DEBUG)` in application code. The
  component reads its log level from the config model and applies it via
  `logging.getLogger().setLevel(…)` at startup.
- **Per-request level override via `structlog.contextvars` — operator-only.**
  The correlation middleware (rule 4) MAY bind a lowered effective level
  for one request's span, but only when the request is from an
  **authenticated operator identity** or an **internal caller** (an
  allowlisted service identity on the internal network). A client-supplied
  `?debug=1` query parameter or `X-Debug: true` header on an
  unauthenticated request MUST be ignored. DEBUG records are where request
  and response payloads tend to get dumped (see rule 6). An override that
  any caller can trigger lets that caller pull sensitive data into the logs
  and flood the log stream on demand.

```python
# In the config model
from pydantic import BaseModel

class Config(BaseModel):
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
```

**Failure prevented:** DEBUG-on-by-default in production flooding the log
stream with per-retry and per-query records, exhausting the log-shipper's
throughput budget and burying actionable ERROR and WARNING events under
noise. It also prevents an unauthenticated caller from switching on DEBUG
for their own requests to flood the logs or dump payloads into them
(CWE-779).

### 4. Request-logging / correlation middleware

Every deployable HTTP service installs an ASGI middleware that:

1. **Reads the correlation id from the `X-Request-ID` header** (validating
   it as a UUID) via `asgi-correlation-id`'s `ContextVar`.
2. **Binds `request_id`, `correlation_id`, `path`, and `method`** to
   `structlog.contextvars.bind_contextvars()` at the start of every
   request.
3. **Echoes the correlation id back to the client** in the `X-Request-ID`
   response header, so a caller can quote the id when reporting a problem
   and a cross-service caller can propagate the same id on its next hop.
4. **Clears the contextvars** at the end of every request so no state
   leaks between requests.

```python
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Clear any stale context from a previous request on the same
        # event-loop task (the per-event-loop gotcha — see note below)
        structlog.contextvars.clear_contextvars()

        # Read and validate the correlation id
        correlation_id = request.headers.get("X-Request-ID", "")
        try:
            uuid.UUID(correlation_id)
        except ValueError:
            correlation_id = str(uuid.uuid4())

        structlog.contextvars.bind_contextvars(
            request_id=correlation_id,
            correlation_id=correlation_id,
            path=request.url.path,
            method=request.method,
        )

        logger.info("request_start")

        try:
            response = await call_next(request)
        except Exception:
            logger.exception("request_failed")
            raise
        else:
            # Echo the id back so the client can reference it
            response.headers["X-Request-ID"] = correlation_id
            logger.info("request_finished", status_code=response.status_code)
            return response
        finally:
            structlog.contextvars.clear_contextvars()
```

**Contextvars-per-event-loop gotcha.** `structlog.contextvars` uses
`contextvars.ContextVar`, which is tied to the `asyncio.Task`, not the
event loop. In practice this means context propagates correctly through
`await` calls within the same task. However, frameworks that spawn
background tasks or use thread pools (Starlette's `BackgroundTasks`,
`run_in_executor`) create new tasks/threads that do NOT inherit the
parent's contextvars. Prefer async handlers and dependencies so the
correlation context stays with the request; when a background task must
emit log records tied to the originating request, pass the correlation
id explicitly.

**Optional: expose the id to endpoints via a dependency.** Endpoints that
need the correlation id in their own logic (to return it in a body, or to
forward it on an outbound call) read it from the same context rather than
re-parsing the header — a one-line FastAPI dependency keeps a single source
of truth:

```python
from typing import Annotated
from fastapi import Depends
import structlog

def request_id() -> str:
    return structlog.contextvars.get_contextvars().get("request_id", "")

RequestId = Annotated[str, Depends(request_id)]
```

**Failure prevented:** an error in service B that the operator cannot
trace back to the originating request in service A. Without a
`correlation_id` on every log event across every service, reconstructing
a request's path through the fleet requires aligning timestamps across
N log streams by hand — and clock skew makes that unreliable. With a
single id carried in the `X-Request-ID` header and bound to every log
event, the aggregator's query is `correlation_id = "<id>"` across all
services.

### 5. Disable or redirect uvicorn's own handlers

Uvicorn ships with its own logging configuration — it attaches a
`StreamHandler` with a plain-text formatter to the `uvicorn.access`
and `uvicorn.error` loggers at startup. When the application also
configures structlog as the root handler (rule 1), every access log
event is formatted TWICE: once by uvicorn's plain-text handler and
once by structlog's JSON handler.

To prevent double-formatting, pass `log_config=None` to `uvicorn.run()`
and configure logging entirely in the application:

```python
import uvicorn

uvicorn.run(app, log_config=None)
```

This tells uvicorn to skip its own logging setup entirely. The
application's structlog configuration (rule 1) is the single handler
for ALL loggers — application, uvicorn, and third-party.

**Failure prevented:** every access log event appearing twice in the
log stream — once as uvicorn's `"127.0.0.1:12345 - "GET /health HTTP/1.1" 200"`
plain-text line and once as structlog's `{"event": "request finished",
"status_code": 200, ...}` JSON object. The aggregator sees duplicate
events, and the plain-text line carries none of the structured context
(request id, correlation id) the middleware bound.

### 6. Never log sensitive data

This is the canonical rule for the fleet. Other pages link here instead of
restating it. Following the
[OWASP Logging Cheat Sheet's "Data to exclude"](https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html#data-to-exclude)
list, no log event, at any level including DEBUG, may contain:

- **Credential-carrying headers:** `Authorization`, `Proxy-Authorization`,
  `Cookie`, `Set-Cookie`, `X-Api-Key`, or similar.
- **Access tokens and API keys:** bearer tokens, OAuth access or refresh
  tokens, API keys, including tokens returned in upstream service responses.
- **Passwords:** including passwords received through API request bodies or
  forms.
- **Session identifiers:** session ids, CSRF tokens.
- **Connection strings and encryption keys:** DSNs that carry credentials,
  private keys, signing secrets.
- **PII:** personal data beyond what the operation strictly needs to
  identify the record.
- **Raw request and response bodies, and full URLs with query strings:**
  credentials, tokens and PII regularly travel in both.

Two concrete requirements follow:

1. **The request middleware binds only the fields rule 4 names** —
   `request_id`, `correlation_id`, `path` and `method`. It never logs
   `request.url` (which includes the query string), `request.headers`, or
   the request or response body. The rule 4 middleware binds
   `request.url.path`, not `str(request.url)`. To log a specific header,
   name it explicitly and make sure it is not in the classes above
   (`X-Request-ID` is fine).
2. **A redaction processor runs at the start of the structlog chain.** Put
   a processor that drops or masks sensitive keys before any renderer. It
   catches a secret bound by mistake as a top-level context var or event
   field. It inspects top-level keys only: a secret nested inside a
   dict-valued field is **not** caught. It is a last-line backstop, not a
   guarantee and not permission to log raw objects:

```python
import re

_SENSITIVE = re.compile(
    r"authorization|cookie|password|passwd|token|secret|api[_-]?key|session",
    re.IGNORECASE,
)

def redact_sensitive(_logger, _method, event_dict):
    for key in list(event_dict):
        if _SENSITIVE.search(key):
            event_dict[key] = "[REDACTED]"
    return event_dict

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        redact_sensitive,  # first after context merge — before anything renders
        # … rest of the rule 1 chain …
    ],
)
```

Add the same processor to the `ProcessorFormatter`'s `foreign_pre_chain`
so stdlib records from third-party libraries are covered too. A key-name
processor cannot see a token interpolated into a free-text `event`
message. Requirement 1 and code review cover that case.

The [security-posture audit](security-posture.md#audit) checks this rule
with a **Log hygiene** row: a test that captures log output for a request
carrying `Authorization: Bearer <token>`, plus a grep or Semgrep rule
against logging `request.headers` or `request.url`.

**Failure prevented:** credentials and session tokens written to the log
stream (CWE-532, [OWASP Top 10:2025](https://owasp.org/Top10/2025/) A09 Security
Logging & Alerting Failures). Logs are retained, shipped to an
aggregator and read by everyone with log access. One logged
`Authorization` header hands a working credential to anyone who can query
the logs, long after the request ended and outside the access controls
that protect the secret store.

## Failure modes this prevents

- **Unparsable log stream.** Mixed `print()`, `logging.info("done")`,
  and traceback text in the container log stream forces the aggregator
  to parse ad-hoc formats. Structured JSON eliminates the parser —
  every field is addressable by key.
- **Untraceable cross-service errors.** Without a `correlation_id` on
  every log event, matching a client-side error response to the
  server-side log lines that produced it requires timestamp alignment
  and guesswork. The correlation id ties them together directly.
- **Double-formatted access logs.** Uvicorn's default handler and
  structlog's handler both emit every access event, producing duplicate
  log lines — one structured, one plain-text. Disabling uvicorn's
  handler (`log_config=None`) prevents this.
- **Production log floods.** DEBUG-level-by-default produces
  per-retry, per-query, and per-SQL-statement records that exhaust
  log-shipper throughput and bury actionable events.
- **Aggregator lock-in.** A component that ships directly to a specific
  backend (Loki, Elasticsearch, CloudWatch) hard-codes an observability
  stack assumption. stdout decouples the application from the shipper,
  so the fleet can change aggregators without touching application code.
- **Context leakage between requests.** structlog contextvars bound
  during one request persisting into the next (when the ASGI server
  reuses a task) produces log events with a stale `request_id`,
  corrupting trace reconstruction.
- **Secrets in the log stream.** A logged `Authorization` header, full
  URL with credentials in the query string, or raw request body leaks
  credentials to everyone with log access (CWE-532). Rule 6 forbids it.
  A redaction processor is the backstop, and an unauthenticated caller
  can no longer turn on DEBUG payload dumping.

## Relationship to other standards

- **[HTTP error envelope](http-error-envelope.md)** — mandates that every
  error response carry a `correlation_id` matching the `X-Correlation-ID`
  (`x-correlation-id`) header. This logging standard defines where that
  correlation id originates and how it is bound to every log event,
  making the error-envelope requirement actionable.
- **[Ruff lint rules](ruff-lint-rules.md)** — the `LOG` and `G` rule
  families enforce logging hygiene (no `logging.warn`, no f-strings in
  logging calls, lazy formatting). This logging standard is the
  convention those rules protect — without a logging standard, the
  rules have no anchoring context.
- **[Library internal logging](library-logging.md)** — the lighter-weight
  convention for libraries: `logging.getLogger(__name__)`, `NullHandler`,
  lazy `%`-style formatting, no configuration. Libraries that follow the
  library standard still interoperate with the structlog pipeline because
  `ProcessorFormatter.foreign_pre_chain` bridges stdlib records into the
  JSON renderer.
- **[Component standard](component-standard.md#logging)** — the component
  standard's logging section requires stdout/stderr (never files) and UTC
  ISO-8601 timestamps. This standard builds on that foundation with the
  structured-JSON, correlation, and level-convention rules.
