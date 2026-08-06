# Library internal logging

> **Scope: every Python repository (libraries and deployable components).**
> A package that emits no log records at all is exempt — this only applies
> when the package uses the `logging` module for internal observability.
> This applies *in addition to* the [repo baseline](repo-baseline.md).

Every library package in the fleet follows the standard-library logging
convention for internal observability: a module-level logger, a single
`NullHandler` on the package's top-level logger, no configuration, and
lazy `%`-style formatting. Callers get zero-config visibility into
retries, requests, and errors without wiring their own callbacks.

## The rule

### 1. Module-level logger

Each module that emits log records creates a module-level logger:

```python
import logging

logger = logging.getLogger(__name__)
```

This gives every log record a hierarchical dotted name matching the
package structure (`robotsix_http.client`, `robotsix_http.retry`), so
callers can enable or silence specific subsystems with standard
logger-level configuration.

### 2. One NullHandler on the package's top-level logger

The package's `__init__.py` attaches exactly one `logging.NullHandler()`
to the top-level logger:

```python
# src/robotsix_http/__init__.py
import logging

logging.getLogger(__name__).addHandler(logging.NullHandler())
```

This is the CPython logging HOWTO's recommended pattern for libraries.
A `NullHandler` swallows every record, so importing the package never
triggers the "No handlers could be found for logger …" warning and the
library never prints to stderr unless the application opts in by adding
its own handler.

The handler is attached **once** in `__init__.py`, at the package root.
Individual modules do not add handlers — they only obtain a logger
(`logging.getLogger(__name__)`) and emit records through it.

### 3. Never call `basicConfig`, set levels, or add non-null handlers

The library never calls `logging.basicConfig()`, never sets a level on
any logger (`logger.setLevel(…)`), and never adds a non-null handler
(`StreamHandler`, `FileHandler`, etc.). Logging configuration —
levels, formatting, destinations — is the application's decision.

```python
# ✅  Library obtains a logger and emits records
import logging

logger = logging.getLogger(__name__)

def fetch(url: str) -> bytes:
    logger.debug("fetching %s", url)
    ...

# ❌  Library configures logging — steals control from the application
import logging

logging.basicConfig(level=logging.DEBUG)  # never do this in a library
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)            # never do this either
```

A library that calls `basicConfig` or sets a level on import breaks
every other library in the same process — the first import wins, and
the application's own logging setup is silently overridden.

### 4. DEBUG for routine operational events; WARNING/ERROR for abnormal conditions

Routine operational events — retries, backoff, connection reuse, cache
hits — are emitted at `DEBUG` level:

```python
logger.debug("retrying (%d/%d) after %0.1fs: %s", attempt, max_attempts, delay, reason)
```

Use `WARNING` for conditions the operator should know about but that
don't prevent operation (a deprecated API call, a degraded fallback
path). Use `ERROR` only for genuinely abnormal conditions — a request
that failed after exhausting retries, a corrupt cache entry.

This mirrors urllib3's convention: retry records on the
`urllib3.connectionpool` logger at `DEBUG` level, with the lazy-formatted
`"Retrying (%d/%d) ... %s"` message.

### 5. Always lazy `%`-style formatting — never f-strings

All logging calls use lazy `%`-style formatting with arguments passed to
the logging method:

```python
# ✅  Lazy formatting — the string is only interpolated if the record is emitted
logger.debug("retrying (%d/%d) after %0.1fs", attempt, max_attempts, delay)
logger.warning("degraded fallback to %s: %s", endpoint, exc)

# ❌  f-string — interpolation happens before the logging call, even at
#     levels that are disabled, wasting CPU on every call site
logger.debug(f"retrying ({attempt}/{max_attempts}) after {delay:0.1f}s")
```

An f-string in a logging call eagerly evaluates the string formatting
even when the logger's effective level is above `DEBUG` — the string is
built, then discarded. For a retry loop that emits a record on every
attempt, this is wasted work on every disabled call site.

Enforce this with ruff rule **`G004`** (`flake8-logging-format`), which
flags f-string usage in logging calls. See the [ruff lint rules](ruff-lint-rules.md)
standard for the full `G` rule family.

## Why

Every HTTP, IO, and retry library the fleet ships has the same need:
emit internal observability records so operators can trace what the
library is doing without wiring their own callbacks. urllib3 solved this
with its `urllib3.connectionpool` logger; tenacity exposes a
`before_sleep` hook for the same purpose. Codifying one convention —
the logger hierarchy, the `NullHandler` pattern, the level policy, and
the formatting rule — prevents each repo from inventing its own logger
naming, level policy, or formatting style.

A fleet that shares one convention gives operators one mental model:
enable `DEBUG` on the package logger, see every retry and backoff
decision; enable `WARNING`, see degradations; the records are always
lazy-formatted and never print unless the application opts in.

## Failure modes this prevents

- **"No handlers could be found" on import.** A library that emits log
  records without a `NullHandler` causes the `logging` module to print a
  warning to stderr on the first record. In a container, that warning
  lands in the log stream with no context, confusing operators. The
  `NullHandler` silences it.
- **Library steals logging configuration.** A library that calls
  `basicConfig()` or `setLevel()` on import overwrites the application's
  logging setup. The first import wins; every subsequent library and the
  application itself inherit the library's level and format. The
  `NullHandler`-only rule prevents this.
- **Wasted CPU on disabled debug records.** An f-string in a `logger.debug()`
  call builds the string before the logging call runs, even when `DEBUG`
  is disabled. In a retry loop or a hot path, this is measurable overhead
  with no value. Lazy `%`-style formatting defers the work until the
  record is actually emitted.
- **Inconsistent logger naming.** Without a convention, one library uses
  `logging.getLogger("retry")`, another uses `logging.getLogger("http")`,
  and a third uses `logging.getLogger(__name__)`. Operators can't
  predictably enable or silence a subsystem — they must read each
  library's source to find its logger names. `__name__`-based loggers
  make the hierarchy discoverable from the import path.
- **Mis-leveled records.** A library that logs retries at `WARNING` or
  `ERROR` floods the operator's attention with routine events that don't
  require action. A library that logs genuine failures at `DEBUG` hides
  them unless the operator already knows to turn up verbosity. The
  DEBUG-for-routine / WARNING+ERROR-for-abnormal convention gives
  operators a predictable signal-to-noise ratio.

## Relationship to other standards

- **[Component standard](component-standard.md#logging)** — the logging
  section requires stdout/stderr (never files) and UTC ISO-8601
  timestamps. This standard governs what *libraries* emit; the component
  standard governs where the *process* sends its output. They are
  complementary — a library that follows this standard produces records
  the component standard's sink will capture.
- **[Ruff lint rules](ruff-lint-rules.md)** — the `G` rule family
  (`flake8-logging-format`) enforces lazy formatting. Rule `G004`
  specifically catches f-strings in logging calls. Repos that adopt this
  standard should also adopt the `G` rules.
- **[Python practices](python.md)** — the Python practices standard
  references the component standard's logging section for process-level
  output conventions. This standard adds the library-internal
  observability layer on top.
