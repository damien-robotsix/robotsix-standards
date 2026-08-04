# FastAPI test isolation via dependency overrides

> **Scope: deployable components that expose a FastAPI (or Starlette)
> application.** A component whose only HTTP surface is the mandatory
> `/health` endpoint (see the [component standard](component-standard.md))
> does not need this. This applies *in addition to* the
> [repo baseline](repo-baseline.md) and [component standard](component-standard.md).

FastAPI backends that hold mutable server state — in-memory stores, caches,
connection pools, or other per-session objects — have two options for exposing
that state to tests: import the module-level global directly and mutate it, or
wire the state through a FastAPI dependency that tests can override. The first
option (import-and-mutate) is the anti-pattern this standard replaces.

## Why this exists

Importing and clearing a module-level store from a test fixture couples tests
to implementation detail, leaks state across tests, and skips FastAPI's
lifespan startup/shutdown handlers:

1. **Implementation coupling.** Tests import a private module variable
   (`games`, `cache`, `pool`) rather than exercising the dependency wiring
   the application actually uses. A refactor that moves the store into a
   different module or wraps it in a class breaks every test fixture.

2. **State leakage.** If one test forgets to clear the store (or fixture
   ordering changes), a global store accumulates leftover state and later
   tests receive polluted data. Cross-test interference at the store level
   is invisible to the test runner until a failure materialises in a
   seemingly unrelated test.

3. **No teardown hook.** A `dependency_overrides` entry with an autouse
   fixture that calls `app.dependency_overrides.clear()` gives automatic
   per-test isolation with zero teardown logic — no `finally` block, no
   manual cleanup.

4. **Lifespan skipped.** Using `TestClient(app)` without a `with` block
   means ASGI startup/lifespan events never fire. Startup may initialise
   connection pools, load configuration, or warm caches — skipping it
   means tests run against an application in a partially-initialised state
   that does not reflect production.

The FastAPI team's own guidance (the
[testing-dependencies docs](https://fastapi.tiangolo.com/advanced/testing-dependencies/)
and the
[full-stack template](https://github.com/fastapi/full-stack-fastapi-template))
calls `dependency_overrides` the canonical mechanism for test isolation.

## Expose mutable state through a dependency

Every piece of mutable per-session state that tests need to replace **must**
be exposed through a `Depends(get_X)` dependency that returns the current
store:

```python
from fastapi import Depends, FastAPI

# Module-level store — NEVER imported by tests.
_games: dict[str, Game] = {}


def get_games() -> dict[str, Game]:
    """Return the current game store."""
    return _games


app = FastAPI()


@app.get("/games")
async def list_games(games: dict[str, Game] = Depends(get_games)):
    return list(games.values())
```

The dependency is the single access point. Route handlers, service functions,
and middleware all consume the store through the same `Depends(get_games)`
injection — never by importing `_games` from the module.

**Failure mode:** a route handler imports `_games` directly while tests
override `get_games` via `dependency_overrides`. The handler bypasses the
override and reads/writes the production store — tests and application logic
operate on different state, producing false passes (the test asserts against
override state the handler never touched) or false failures (the handler
pollutes the test's override with production data).

## Override dependencies in tests

### Autouse fixture with `dependency_overrides.clear()`

The canonical test fixture is an autouse, function-scoped fixture that sets
each mutable-state dependency to a fresh store and clears all overrides on
teardown:

```python
import pytest
from fastapi.testclient import TestClient
from my_service.main import app, get_games


@pytest.fixture(autouse=True)
def override_dependencies():
    """Replace every mutable-state dependency with a fresh store per test."""
    app.dependency_overrides[get_games] = lambda: {}
    yield
    app.dependency_overrides.clear()
```

- **`autouse=True`** ensures every test in the module or session gets a
  clean store without importing the fixture manually.
- **`yield`** runs the test body; `app.dependency_overrides.clear()` on
  teardown resets the override registry so no override leaks to the next
  test.
- **`lambda: {}`** returns a fresh mutable store per call. For more complex
  setup, a factory function that constructs a fresh store is fine — the key
  is that the override returns a new object, not a shared global.

**Failure mode:** an autouse fixture that sets the override but never calls
`app.dependency_overrides.clear()` on teardown — overrides accumulate across
tests, and a later test that does not set the override for `get_games` still
inherits a stale override from an earlier test that did.

### Never import and mutate the module-level store

A test fixture that reaches into the application module and mutates the
private store directly violates this standard:

```python
# ANTI-PATTERN — do not do this.
import my_service.main

@pytest.fixture(autouse=True)
def clear_games():
    my_service.main._games.clear()
```

This couples the test to the exact module path and variable name of the
store. A rename or reorganisation breaks the fixture, and the test suite
gives no warning — `_games.clear()` silently succeeds on a store the
application no longer uses.

### Per-test `with TestClient(app) as client:`

Prefer a `with` block so that ASGI lifespan/startup handlers actually run:

```python
def test_list_games_empty():
    with TestClient(app) as client:
        response = client.get("/games")
        assert response.json() == []
```

The `with` block triggers `startup` and `shutdown` lifespan events. Tests
that exercise startup-dependent state (connection pools, warmup caches,
background-task schedulers) run against a fully-initialised application.

A module-scoped `client` fixture that wraps the `with` block is also
acceptable:

```python
import pytest
from fastapi.testclient import TestClient
from my_service.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client
```

**Failure mode:** `TestClient(app)` used as a bare value (no `with` block,
no context manager) — the `startup` lifespan event never fires. Connection
pools stay `None`, caches stay cold, and tests pass against a
never-initialised application, masking bugs that only surface in production.

## Cross-reference

- **[FastAPI Pydantic field descriptions](fastapi-pydantic-field-descriptions.md)** —
  the other fleet-wide FastAPI convention: every public request/response field
  must carry `Field(description=...)`.
- **[Pytest shared state builders](pytest-shared-state-builders.md)** —
  root-conftest placement and `make_<thing>` factory fixtures — the
  underlying test-state strategy this page's dependency-override pattern
  builds on.
- **[Pytest practices](pytest.md)** — strictness settings
  (`filterwarnings`, `xfail_strict`, `--strict-markers`) that every test
  suite must adopt.
