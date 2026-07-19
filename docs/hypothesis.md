# Hypothesis property-based testing

> **Scope: every Python repository that uses
> [Hypothesis](https://hypothesis.readthedocs.io/).** These rules apply
> fleet-wide; repos that do not use Hypothesis are unaffected.

## Why this exists

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
