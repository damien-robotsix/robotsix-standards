# Pytest strictness configuration

> **Scope: every Python repository.** These settings apply fleet-wide so
> every test suite fails loudly on deprecation warnings, unregistered markers,
> and unexpectedly-passing xfails.

## Why this exists

Without strictness settings, pytest silently ignores several classes of
problem that matter in CI:

- **Deprecation warnings from dependencies scroll past invisibly** — the
  first a team learns of a removed API is the upgrade that breaks at runtime.
- **Typos in `@pytest.mark.xxx` decorators are silently tolerated** — the
  marker is registered as an ad-hoc string, the test runs without it, and the
  intended filtering or skipping never happens.
- **`@pytest.mark.xfail` tests that start passing** (because the bug was
  fixed) continue to report as "expected failure" — the test suite never
  signals that the fix landed, so the xfail marker rots indefinitely.

Four mature ASGI/data projects — FastAPI, Starlette, Pydantic, and httpx —
all ship `filterwarnings = ["error"]` in their `pyproject.toml`. FastAPI and
Starlette additionally enable `--strict-markers` and `--strict-config`.
Codifying the convention here means every fleet repo inherits the same
discipline rather than each re-deriving it.

## Baseline settings (mandatory)

Every Python repository **must** include these two settings in
`[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error"]
xfail_strict = true
```

- **`filterwarnings = ["error"]`** — turn every warning into an exception.
  This is the universal baseline across all four surveyed projects.
- **`xfail_strict = true`** — an `@pytest.mark.xfail` test that unexpectedly
  passes is reported as a failure (`XPASS(strict)`), flagging the stale
  marker so it can be removed.

**Failure mode:** without `filterwarnings = ["error"]`, dependency
deprecation warnings are invisible in CI output — the upgrade that removes
the deprecated API lands as a surprise breakage. Without `xfail_strict`,
fixed bugs stay marked as expected failures forever, and the test suite
never signals that the fix is real.

## Targeted warning ignores

Repos **may** add narrowly-scoped `ignore:` entries for third-party
`DeprecationWarning`s that are out of their control.

Pytest's `filterwarnings` uses Python's warning filter syntax:
`"action:message:category:module:lineno"`.  The `message` field is matched
as a regex prefix — an entry ending in `...` matches any suffix (the
trailing `...` is `.*`).  When a field is omitted entirely, it matches
anything; an empty string between colons matches an empty string literally.

The two common patterns:

**Category-and-module targeting** (Starlette, Pydantic style):

```toml
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:third_party_package.*:",
    "ignore::DeprecationWarning:another_package.module:",
]
```

**Message-prefix targeting** (httpx style):

```toml
filterwarnings = [
    "error",
    "ignore: You seem to already have a custom sys.excepthook handler installed...",
    "ignore: You seem to already have a custom MultiError...",
]
```

Each `ignore:` entry **must** narrow the scope to the specific warning
it targets — never a bare `"ignore::DeprecationWarning"`.  Starlette,
Pydantic, and httpx all follow this pattern.

**Failure mode:** a bare `ignore::DeprecationWarning` suppresses every
deprecation in the entire test suite, including the project's own — the
setting becomes self-defeating.

### Adding ignore entries safely

After enabling `filterwarnings = ["error"]`, run the full test suite.
Only add `ignore:` entries for warnings that are both genuinely benign
**and** unfixable by the project — i.e. third-party deprecations whose
fix is upstream.  Every `ignore:` line should cite the specific warning
message or module it suppresses, so a future contributor can re-evaluate
whether the ignore is still needed.

**Failure mode:** adding `ignore:` entries preemptively ("just in case")
accumulates stale suppressions that hide new warnings indefinitely.

### Async test drivers and nested-event-loop hazards

When a test helper internally calls `asyncio.run()` (or any other function
that starts a new event loop), that helper **must** be exercised only from
synchronous test functions — never from an `async def test_*` that is
already running inside an event loop.  With `filterwarnings = ["error"]`,
an attempted nested event loop surfaces as a hard test failure
(e.g. `RuntimeError` or `DeprecationWarning` from the async library).

**Failure mode:** a sync test driver called from an async test function
crashes inside CI only after the warning-as-error baseline is enabled,
blocking unrelated work while the team diagnoses the nested-loop failure.

## Recommended tier: strict markers and config

Repos **should** additionally enable marker and config strictness:

```toml
addopts = ["--strict-markers", "--strict-config"]
```

- **`--strict-markers`** — any `@pytest.mark.xxx` decorator whose marker
  name is not registered (via `markers` in `pyproject.toml` or a
  `pytest_configure` hook) raises an error instead of silently adding an
  ad-hoc marker.
- **`--strict-config`** — any unrecognised `[tool.pytest.ini_options]` key
  raises an error, catching typos in config.

FastAPI and Starlette both ship these settings.

**Failure mode:** without `--strict-markers`, a typo like
`@pytest.mark.smoke` (intended `smoke`) becomes a silently-registered ad-hoc
marker that no `-m` filter ever selects — the test is never run in the
targeted suite, and the mistake is invisible until a human notices the test
is missing from CI results.

## Full example

```toml
[tool.pytest.ini_options]
addopts = ["--strict-markers", "--strict-config"]
xfail_strict = true
filterwarnings = [
    "error",
    # Third-party deprecation warnings that the project cannot fix:
    # "ignore::DeprecationWarning:some_library.*:",
]
```

## Optional test dependencies — `importorskip` guard

> **Scope: every Python repository that declares optional test dependencies**
> in `[project.optional-dependencies]` (any extra).  The rule applies to any
> module-level `import` in a test file that references a package **not**
> listed in the project's unconditional (bare) `dependencies`.

### Why this exists

`pytest` imports every test module during **collection**, before any test
runs.  An unguarded module-level `import <optional-dep>` therefore breaks
the whole test suite with `ModuleNotFoundError` — it does **not** defer the
failure to the tests that use it.  When the optional dependency is absent,
the suite cannot even start.

Guarding with `pytest.importorskip` (at module scope, before the import)
makes pytest report the affected tests as `skipped` when the optional
dependency is missing, so the suite still collects and runs the remaining
tests.

### Rule

Every **module-level import of an optional dependency** in a test file must
be guarded with `pytest.importorskip("<module>")` placed **immediately before**
the guarded `import` statement.

**Pattern:**

```python
import pytest

pytest.importorskip("hypothesis")
from hypothesis import given, settings  # guarded — only reached if hypothesis is installed
```

A conditional import (`try: ... except ImportError: ...`) is an acceptable
alternative when the test file needs to import the optional module
conditionally, but `importorskip` is preferred because it integrates with
pytest's skip reporting and is the canonical mechanism.

**Failure mode:** an unguarded module-level `import <optional-dep>` causes
`ModuleNotFoundError` at collection time, preventing the **entire** test
suite from running — not just the tests that need the dependency.  A
contributor running `pytest` without the `[dev]` extra installed gets a
crashed suite with no indication of which dependency is missing or which
tests are affected.

### Adoption by the ecosystem

All prominent typed projects apply exactly this pattern at module scope,
before the optional-extra imports:

- **pandas** — guards optional-backend test files with `importorskip`
  (including `minversion` forms).
- **Pydantic** — module-level `importorskip` for optional extras
  (`email-validator`, `python-dotenv`, `orjson`, `Babel`) so the suite
  collects cleanly without them.
- **FastAPI** — same for SQLAlchemy and version-specific test files.

### Fleet exemplar

`robotsix-config` already codifies this in its `AGENT.md` and follows it:
`tests/config/test_config_properties.py` calls
`pytest.importorskip("hypothesis")` at line 9, immediately before the
`from hypothesis import ...` at lines 12-13.

Repos that follow this standard should also consider adding a CI guardian
job that mechanically verifies every module-level optional-dependency
import in `tests/` is guarded, preventing regressions.

## Cross-reference

- **[Pytest shared state builders](pytest-shared-state-builders.md)** —
  root-conftest placement and `make_<thing>` factory fixtures for reusable
  test-state builders across test packages.
