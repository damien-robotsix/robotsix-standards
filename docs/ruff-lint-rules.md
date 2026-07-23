# Ruff lint rules

> **Scope: every Python repository.** These rules extend the baseline ruff
> configuration (see [Python practices](python.md#lint-types-and-security-lint))
> with a shared set of Tier 2 rule families. Every Python repo SHOULD adopt
> them; the per-file ignores and the PT006 exclusion are the recommended
> defaults.

## Why this exists

The fleet's baseline ruff configuration — E, F, I, W, S — catches
correctness errors, import order, and basic security anti-patterns.
But repos that also enable Tier 2 rule families (Pydantic, FastAPI, httpx)
catch more: dead parameters, non-idiomatic comprehensions, performance
anti-patterns, and inconsistent pytest style. Without a shared convention,
each repo independently discovers and configures these rules, leading to
inconsistent code quality enforcement across projects.

This standard defines one recommended Tier 2 set — ARG, C4, PERF, PT —
with per-file ignores and one deliberate exclusion (PT006), so every repo
gets the same coverage without reinventing the decision.

## Rule families

### ARG — flake8-unused-arguments

Catches unused function parameters that confuse readers and accumulate
cruft. Near-zero false positives in production code when suppressed in
tests.

**Failure prevented:** a parameter that was once used, then the logic
that consumed it was removed, but the signature was never cleaned up.
Every caller still passes it, every reader still studies it, and nobody
knows it's dead.

### C4 — flake8-comprehensions

Encourages idiomatic comprehensions — e.g. `list(x for x in ...)` →
`[x for x in ...]`, `dict((k, v) for k, v in ...)` → `{k: v for k, v
in ...}`.

**Failure prevented:** generator expressions fed to type constructors
(`list(...)`, `dict(...)`, `set(...)`) add a function-call frame and are
slower than the equivalent comprehension syntax. The comprehension form
is also the standard idiom readers expect.

### PERF — perflint

Catches micro-performance issues like redundant `.keys()` calls on dicts
(`d.keys() | other.keys()` can be `d | other`), unnecessary `.copy()`
calls, and inefficient membership tests.

**Failure prevented:** performance anti-patterns that are individually
cheap but accumulate across hot paths — a `.keys()` call in a loop that
runs thousands of times, or an `O(n)` list membership test where a set
would be `O(1)`.

### PT — flake8-pytest-style

Enforces consistent pytest patterns: `@pytest.fixture()` over
`@pytest.fixture`, `@pytest.mark.xfail` over `@pytest.mark.xfail()`,
assertions over `assert True`/`assert False`, and so on.

**Failure prevented:** inconsistent test style that makes the test suite
harder to read and review — two adjacent test files using different
spellings of the same concept, or a bare `@pytest.fixture` that silently
differs from `@pytest.fixture()` in a way that matters.

## Configuration

Add to `pyproject.toml`:

```toml
[tool.ruff.lint]
extend-select = [
    "ARG",   # flake8-unused-arguments
    "C4",    # flake8-comprehensions
    "PERF",  # perflint
    "PT",    # flake8-pytest-style
]
ignore = ["PT006"]

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["ARG"]     # test helpers often have unused signature-matching args
"__init__.py" = ["ARG"]  # re-exports may have unused args
```

### PT006 exclusion

PT006 (parametrize argument style) is deliberately excluded via
`ignore = ["PT006"]`. The rule enforces `pytest.param(...)` wrapping
in `@pytest.mark.parametrize`, but the list-of-tuples style is widely
preferred in the Python ecosystem and is considered an acceptable
convention:

```python
# Preferred — list-of-tuples, no pytest.param() wrapping:
@pytest.mark.parametrize(
    ("input", "expected"),
    [(1, 2), (3, 4), (5, 6)],
)
def test_add(input, expected):
    assert input + 1 == expected
```

### Combining with the baseline

These rules are additive — repos that already enable the baseline
rule set (E, F, I, W, S) add `extend-select` for the Tier 2 families.
The per-file ignores for `tests/**` and `__init__.py` are compatible
with the existing `S`-rule ignores documented in [Python
practices](python.md#lint-types-and-security-lint).

## Migration path

1. Add `extend-select = ["ARG", "C4", "PERF", "PT"]` and
   `ignore = ["PT006"]` to `[tool.ruff.lint]` in `pyproject.toml`.
2. Add the per-file ignores for `tests/**` and `__init__.py`.
3. Run `ruff check` and fix or whitelist any violations. Fleet
   experience shows typically zero to a handful of violations across
   all four rule families.

## Source references

- **Pydantic** enables ARG, C4, PERF alongside E, F, I, N, UP, B, SIM,
  RUF, PIE, T10 in its `pyproject.toml`.
- **FastAPI** enables ARG, C4, PT alongside E, F, I, N, UP, B, SIM, RUF, S.
- **httpx** takes the `select = ["ALL"]` approach and ignores specific
  rules — demonstrating that broad rule coverage is the industry direction.
