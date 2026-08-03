# Pytest shared state builders

> **Scope: every Python repository with more than one test package.**
> These rules apply fleet-wide; single-package repos are unaffected.

## Why this exists

When a test suite grows beyond a single package, shared test-state builders
— game-state factories, environment constructors, database-population helpers
— tend to scatter across two wrong places:

- **Inline construction duplicated in every test module** — the same
  `HexarchyEnv(num_players=2, render_mode="ansi")` plus
  `env.reset(seed=42)` and a step-loop appears verbatim in every test
  function that needs an environment, because no shared factory is
  available.
- **`conftest.py` files scoped too deep** — fixtures defined in
  `tests/core/conftest.py` are only visible to `tests/core/` and its
  descendants; sibling packages (`tests/env/`, `tests/agents/`,
  `tests/server/`) cannot import or inherit them, so they reinvent the
  same builders.

The two rules below — root-conftest placement and factory-fixture naming —
remove duplicated inline construction, make builders reusable across every
test package, and keep each test isolated with a fresh instance.

## Root conftest placement

Shared state-building helpers that are used by more than one test package
**must** live in a single root `tests/conftest.py` (or a `tests/_utils/`
module whose fixtures are re-exported from the root conftest).

pytest discovers fixtures by walking each test module's directory tree
**upwards** — a fixture in `tests/conftest.py` is visible to every test
under `tests/`, while a fixture in `tests/core/conftest.py` is visible
only to `tests/core/` and its subdirectories. Placing shared builders in
the root conftest makes them available to the entire test suite without
imports or duplication.

Per-subdirectory `conftest.py` files **should** be reserved for
directory-specific fixtures or parent-override hooks — not for
builders that sibling packages also need.

**Failure mode:** a fixture defined in `tests/core/conftest.py` is
invisible to `tests/env/test_env.py`. The env test author either
copies the builder inline (duplication) or moves the fixture to a
deep conftest that still doesn't help the next sibling package. The
fleet observed this in the robotsix-mill/hexarchy `tests/` tree,
where `tests/core/conftest.py` held game-state fixtures that
`tests/env/`, `tests/agents/`, and `tests/server/` all needed but
could not reach.

## Factory fixtures for mutable objects

When the built object is **mutated during the test** — game states,
RL/PettingZoo environment instances, mutable ORM models — expose it
as a **factory fixture** whose canonical name is `make_<thing>` and
whose return value is function-scoped (fresh instance per call).

```python
import pytest
from mygame import GameState


@pytest.fixture
def make_game_state():
    """Return a new GameState factory — one fresh instance per call."""
    def _make(num_players: int = 2, seed: int = 42):
        state = GameState(num_players=num_players)
        state.reset(seed=seed)
        return state
    return _make
```

A test calls the factory to get its own instance:

```python
def test_scoring(make_game_state):
    state = make_game_state(num_players=3)
    assert state.num_players == 3
    state.score(0, 10)       # mutation is safe — this test owns the instance
    assert state.scores[0] == 10


def test_scoring_isolation(make_game_state):
    state = make_game_state(num_players=2)
    assert state.scores == [0, 0]   # unaffected by the previous test's mutation
```

This is a **factory fixture** — the fixture itself is a function that
the test calls with parameters — not a **value fixture** that returns
a single shared instance. A value fixture that returns a mutable object
would leak mutations between tests, producing order-dependent failures.

The `make_` prefix is the canonical naming convention (consistent with
[PettingZoo](https://github.com/Farama-Foundation/PettingZoo) and
other RL/framework suites) so every test author knows at a glance that
the fixture returns a fresh instance per call.

**Failure mode:** a shared value fixture for a mutable object causes
order-dependent test failures — test A mutates the state, test B
receives the mutated residue, and the suite passes or fails depending
on execution order. Order-dependent failures are notoriously hard to
diagnose because they vanish when the failing test is run in isolation.

## Value fixtures as factory callers

Where convenient, existing single-implementation value fixtures **may**
remain as thin callers of the factory — they reduce boilerplate for the
common case while the underlying `make_` factory stays available for
tests that need a non-default configuration:

```python
@pytest.fixture
def game_state(make_game_state):
    """Default two-player game state for tests that don't need a custom config."""
    return make_game_state()
```

Tests that need the default get it without calling the factory; tests
that need a custom configuration call `make_game_state(num_players=4)`
directly. Both paths route through the same builder, so the construction
logic stays in one place.

## Cross-reference

- **[Pytest practices](pytest.md)** — strictness settings (`filterwarnings`,
  `xfail_strict`, `--strict-markers`) that every test suite must adopt.
- **[Hypothesis testing](hypothesis.md)** — property-based testing profiles
  and shared strategies (another form of reusable test-state builder).
- **[Async SQLAlchemy test fixtures](async-sqlalchemy-test-fixtures.md)** —
  a concrete example of the root-conftest + factory pattern applied to
  database sessions.
