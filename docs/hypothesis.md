# Hypothesis property-based testing

> **Scope: every Python repository.** [Hypothesis](https://hypothesis.readthedocs.io/)
> is the fleet's recommended tool for property-based testing. The mandatory
> rules below apply to repositories that adopt it; repos that do not use
> Hypothesis are unaffected.

## Why adopt Hypothesis

Property-based testing catches the edge cases example-based tests miss.
Instead of asserting a handful of hand-picked inputs, a property test states
an *invariant* and lets Hypothesis generate hundreds of random inputs per
run, shrinking any failure to a minimal reproducer that can be pasted into a
regression test. Fleet game-engine and simulation projects (Nashpy,
fastbreak) have already demonstrated the value:

- **Nashpy** uses `@given` plus `numpy` array strategies to verify
  payoff-matrix invariants — shape preservation and zero-sum detection —
  across arbitrary matrix shapes and values.
- **`RuleBasedStateMachine`** wraps a simulation loop and re-checks its
  invariants after every state transition — the pattern for repos with
  complex state: game engines, agent simulators, and data pipelines.

**Hypothesis augments example-based tests; it does not replace them.**
Example-based tests still cover known edge cases and regression scenarios;
property-based tests cover the unknown ones. Repos keep both.

## Dependency declaration

Every Python repo that adopts Hypothesis **must** declare it as a dev/test
dependency. Dev tooling lives in the PEP 735 `[dependency-groups] dev` group
(see [Python practices](python.md#packaging) for the canonical dev-tooling
placement), so `hypothesis` goes there — not in the unconditional
`[project] dependencies`:

```toml
[dependency-groups]
dev = [
    "hypothesis",
    # ... existing dev/test dependencies ...
]
```

**Failure mode:** Hypothesis is a test-only tool. Declaring it in the
unconditional `dependencies` ships it in the installed library or service
image, bloating the production install with a package nothing imports at
runtime. Declaring it in a bespoke extra instead of the shared `dev` group
splits the test toolchain — a contributor syncing `dev` gets everything
except Hypothesis, and their property tests fail with `ModuleNotFoundError`.

## Writing property-based tests

Write property-based tests for functions with a clear invariant. State the
invariant once with `@given` and let Hypothesis generate the inputs:

```python
from hypothesis import given
from hypothesis import strategies as st

@given(radius=st.integers(min_value=0, max_value=10))
def test_hex_map_has_expected_locations(radius):
    hexes = generate_hex_map(radius)
    assert len(hexes) == 3 * radius * (radius + 1) + 1

@given(radius=st.integers(min_value=1, max_value=10))
def test_centre_hex_is_capital(radius):
    hexes = generate_hex_map(radius)
    assert hexes[(0, 0)] == CAPITAL
```

A good candidate has an invariant that holds for *every* valid input — a
round-trip (serialize then parse returns the original), an idempotency
(wrapping twice equals wrapping once), a shape/size relationship, or a
conservation law. When you can only enumerate edge cases by hand, you do not
have a property; keep those as example-based tests instead.

**Failure mode:** property tests written around behaviour without a real
invariant degrade into weak assertions (e.g. "calling the function does not
crash") that pass for the wrong reasons and add runtime without adding
confidence. Property tests pay for themselves only when the property is the
spec.

## Domain-valid composite strategies

Complex inputs often need to respect domain constraints (a valid UID, a
non-empty name, a reachable hex coordinate). Define those once with
`@st.composite` so every generated value is valid, instead of generating
invalid values and filtering them in the test:

```python
from hypothesis import strategies as st

@st.composite
def hex_map(draw, max_radius: int = 10):
    radius = draw(st.integers(min_value=0, max_value=max_radius))
    return generate_hex_map(radius)
```

Composite strategies compose smaller strategies with `draw`, keeping the
domain rules in one place. Reuse them across tests via the
[shared strategies module](#shared-strategies-module) so a constraint change
is made once, not in every test.

**Failure mode:** strategies that generate mostly-invalid values force tests
to reject inputs (`assume(...)` chains) and waste most of their generation
budget; slow filtering trips Hypothesis health checks and hides real coverage
gaps.

## Stateful invariants with `RuleBasedStateMachine`

For game engines, agent simulators, and data pipelines — anything whose
correctness is "no matter what sequence of operations happens, the invariants
hold" — use `RuleBasedStateMachine`. It wraps the loop, applies generated
operations as `rule()` steps, and re-checks `invariant()` methods after every
transition:

```python
from hypothesis import strategies as st
from hypothesis.stateful import RuleBasedStateMachine, invariant, rule

class SimulationMachine(RuleBasedStateMachine):
    def __init__(self):
        super().__init__()
        self.sim = Simulation()

    @rule(steps=st.integers(min_value=1, max_value=100))
    def advance(self, steps):
        self.sim.advance(steps)

    @invariant()
    def resources_are_conserved(self):
        assert self.sim.total_resources() == self.sim.initial_resources

    @invariant()
    def dimensions_are_preserved(self):
        assert self.sim.world.width == self.sim.world.initial_width
        assert self.sim.world.height == self.sim.world.initial_height

TestSimulation = SimulationMachine.TestCase
```

Use stateful machines for **resource conservation**, **dimension
preservation**, and **consistency across state transitions** — the invariants
that example-based tests cannot enumerate because the operation sequences are
unbounded.

**Failure mode:** a stateful simulation tested only with fixed scripted
scenarios verifies the *paths you thought of*; a `RuleBasedStateMachine`
verifies the invariants across *every* generated sequence, and Hypothesis
shrinks a failing sequence to the shortest one that still breaks the
invariant — a minimal reproducer instead of a 1000-step log.

## Why a shared profile convention

Multiple fleet repos use Hypothesis for property-based testing. Without a
shared convention each repo independently reinvents settings decoration —
repeating `@settings(max_examples=200, derandomize=True, deadline=None,
suppress_health_check=[...])` on every test — and has no shared strategy
module for reusable generators. New contributors waste time hunting for
"what settings do I need?" and copy-pasting boilerplate from nearby tests.

Hypothesis ships a built-in `ci` profile that auto-activates when the `CI`
environment variable is truthy, but it sets `max_examples=100` — too low for
serious property-based coverage. Adopting a custom profile per repo gives CI
thorough coverage without slowing local development.

## Profile registration

Every repo that uses Hypothesis **must** register two profiles in
`tests/conftest.py` — one for CI, one for local development — and load the
active profile from an environment variable.

```python
import os

from hypothesis import HealthCheck, settings

settings.register_profile(
    "ci",
    max_examples=200,          # tunable per-project; must be higher than the built-in 100
    derandomize=True,
    deadline=None,
    database=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.register_profile(
    "dev",
    max_examples=50,
    deadline=5000,
    database=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))
```

- **Default is `"dev"`** — fast and local-friendly. `database=None` keeps
  the example database in memory so it does not survive test sessions (the
  persistent `~/.hypothesis/examples/` directory causes false regressions
  when examples from a stale run are replayed in a later one).
- **CI profile sets `max_examples=200`** (or higher, tuned per-project),
  `derandomize=True` for reproducible failures, and `deadline=None` to avoid
  timing flake in shared CI runners.
- **CI workflows set `HYPOTHESIS_PROFILE=ci`** via an `env:` block on the
  test step. The `--hypothesis-profile ci` CLI flag also works for manual
  overrides.

**Failure mode:** without a registered profile, a repo either uses the
built-in `ci` profile (`max_examples=100`, inadequate) or carries no profile
at all — every test author must repeat the same `@settings(...)` decoration
by hand, and missed settings cause CI flake (missing `deadline=None`) or
false passes (too few examples).

## Shared strategies module

Strategies reused across multiple test modules **must** live in a single
`tests/strategies.py` module, imported by any test file that needs them.

```python
# tests/strategies.py
from hypothesis import strategies as st

text_no_control_chars = st.text(
    st.characters(blacklist_categories={"Cc", "Cs"}), min_size=1
)
valid_uids = st.from_regex(r"^[a-f0-9]{24}$")
iso_dates = st.dates(min_value=date(2000, 1, 1)).map(str)
```

**Failure mode:** strategies copy-pasted across test modules drift (one file
adds a blacklist category, the other doesn't) and make it unclear which
version is canonical. A single shared module is the single source of truth
and makes it easy to discover existing strategies when writing new tests.

## Per-test overrides

Tests that need different `max_examples`, additional health-check
suppression, or a specific filter **still use `@settings(...)` directly** —
the profile fills defaults; the decorator overrides.

```python
from hypothesis import given, settings

@given(x=st.integers())
@settings(max_examples=500, suppress_health_check=[HealthCheck.filter_too_much])
def test_expensive_property(x):
    ...
```

**No need to remove existing `@settings` decorations.** The profile sets
saner defaults so that new tests do not have to repeat boilerplate.

**Failure mode:** stripping `@settings` from every test that already has it
is unnecessary churn and risks dropping legitimate per-test overrides. The
profile is a baseline, not a straitjacket.

## CI workflow

Every repo's CI test step **must** set `HYPOTHESIS_PROFILE=ci`:

```yaml
- name: Run tests
  run: uv run pytest
  env:
    HYPOTHESIS_PROFILE: ci
```

**Failure mode:** without the env var, CI runs the `dev` profile
(`max_examples=50`), giving one-quarter the statistical power the project
intended. The bug that would have been caught at 200 examples slips through,
and the property-based test suite is effectively half-strength in the one
environment where thoroughness matters most.

Property-based tests run in the **same** pytest job as example-based tests —
there is no separate "Hypothesis" CI job. The ordinary `pytest` invocation
collects and runs `@given` tests exactly like any other test, so the existing
coverage gate and test step cover them automatically.

Two Hypothesis CLI flags are worth using in CI:

- `--hypothesis-show-statistics` — prints per-test statistics (examples run,
  health-check status) so reviewers can see how much each property exercised.
- `--hypothesis-seed <int>` — replays a specific generated input sequence.
  The failing seed is printed on every Hypothesis failure and makes flaky or
  intermittent property failures reproducible.

**Failure mode:** a dedicated Hypothesis job drifts from the main suite — it
loses the shared `HYPOTHESIS_PROFILE` env, the coverage gate, and the
`dev`-group install guarantees — and quickly becomes the job nobody runs
locally. Folding property tests into the ordinary pytest invocation keeps
them under the same CI contract as every other test.
