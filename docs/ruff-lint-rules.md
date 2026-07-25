# Ruff lint rules

> **Scope: every Python repository.** These rules extend the baseline ruff
> configuration (see [Python practices](python.md#lint-types-and-security-lint))
> with a shared set of Tier 2 rule families. Every Python repo SHOULD adopt
> them; the PT006 exclusion is the recommended default.

## Why this exists

The fleet's baseline ruff configuration — E, F, I, W, S — catches
correctness errors, import order, and basic security anti-patterns.
But repos that also enable Tier 2 rule families (Pydantic, FastAPI, httpx)
catch more: over-complicated code, non-idiomatic comprehensions, logging
mistakes, commented-out dead code, and inconsistent pytest style. Without a shared convention,
each repo independently discovers and configures these rules, leading to
inconsistent code quality enforcement across projects.

This standard defines one recommended Tier 2 set — SIM, C4, LOG, G, ERA,
PGH, RUF, PT — with one deliberate exclusion (PT006), so every repo gets
the same coverage without reinventing the decision.

## Rule families

### SIM — flake8-simplify

Catches over-complicated code that can be expressed more simply —
nested `if` blocks that collapse to a single condition, `yoda`
conditions (`"value" == variable`), redundant `if-else` assignments,
and verbose context-manager patterns.

**Failure prevented:** code that works but is harder to read and
review than necessary — a triple-nested `if` where a single boolean
expression is equivalent, or a `for`-loop accumulator that the
stdlib already provides as a one-liner. Simplifications make
intent clearer and reduce the surface for off-by-one errors.

### C4 — flake8-comprehensions

Encourages idiomatic comprehensions — e.g. `list(x for x in ...)` →
`[x for x in ...]`, `dict((k, v) for k, v in ...)` → `{k: v for k, v
in ...}`.

**Failure prevented:** generator expressions fed to type constructors
(`list(...)`, `dict(...)`, `set(...)`) add a function-call frame and are
slower than the equivalent comprehension syntax. The comprehension form
is also the standard idiom readers expect.

### LOG — flake8-logging

Catches misuse of the stdlib `logging` module — `logging.warn` (deprecated
in favour of `logging.warning`), `warnings.warn` with a `logging`-style
format string, and `logger.exception` used outside an exception handler.

**Failure prevented:** logging calls that silently degrade — `logging.warn`
exists but is deprecated and may be removed; `logger.exception` outside an
`except` block logs a traceback with no exception, confusing operators.

### G — flake8-logging-format

Checks logging statements for `printf`-style format strings that are
error-prone — missing arguments, extra arguments, or `.format()` calls
that defeat lazy evaluation.

**Failure prevented:** a logging call that raises `ValueError` at runtime
because the format string and arguments don't match, or a logging call
that eagerly evaluates an expensive string formatting even when the log
level is disabled.

### ERA — eradicate

Finds commented-out code blocks. Commented-out code accumulates over time
as developers comment out old implementations "just in case" and never
remove them.

**Failure prevented:** a codebase where 20% of lines are commented-out
dead code that every reader must parse and wonder about — is this
commented out because it's broken, because it's stale, or because it's
a future feature? Version control already keeps the history.

### PGH — pygrep-hooks

Catches Python-specific anti-patterns: `eval()` calls, blanket `# noqa`
suppressions without a specific error code, and `os.getenv` or
`os.environ.get` with no default (returns `None`, which type-checkers
catch but runtime code often doesn't guard against).

**Failure prevented:** `eval()` is a remote-code-execution vector when
fed untrusted input; blanket `# noqa` silences ALL lint rules on a line,
hiding future violations; `os.getenv` without a default produces `None`
that crashes downstream string operations.

### RUF — ruff-specific rules

Ruff's own rule set: ambiguous unicode characters, `asyncio.create_task`
stored without a reference (the task is garbage-collected and cancelled),
mutable dataclass defaults, and collection-iteration while mutating.

**Failure prevented:** a dataclass field defaulting to `[]` that shares
state across all instances (classic Python gotcha); an `asyncio.create_task`
call whose return value is discarded, silently cancelling the task; a
zero-width unicode character in source that looks like nothing but changes
semantics.

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
    "SIM",   # flake8-simplify
    "C4",    # flake8-comprehensions
    "LOG",   # flake8-logging
    "G",     # flake8-logging-format
    "ERA",   # eradicate
    "PGH",   # pygrep-hooks
    "RUF",   # ruff-specific rules
    "PT",    # flake8-pytest-style
]
ignore = ["PT006"]
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
No per-file ignores are needed for this rule set; the Tier 2 families
have low false-positive rates across all file types.

## Migration path

1. Add `extend-select = ["SIM", "C4", "LOG", "G", "ERA", "PGH", "RUF", "PT"]` and
   `ignore = ["PT006"]` to `[tool.ruff.lint]` in `pyproject.toml`.
2. Run `ruff check` and fix or whitelist any violations. Fleet
   experience shows typically zero to a handful of violations across
   all rule families — SIM may flag a few over-complicated conditionals,
   ERA may find commented-out code, and RUF may catch a mutable default.

## Source references

- **Pydantic** enables SIM, C4, RUF alongside E, F, I, N, UP, B, ARG,
  PERF, PIE, T10 in its `pyproject.toml`.
- **FastAPI** enables SIM, C4, RUF, PT alongside E, F, I, N, UP, B, ARG, S
  in its `pyproject.toml`.
- **httpx** takes the `select = ["ALL"]` approach and ignores specific
  rules — demonstrating that broad rule coverage is the industry direction.
