# Single-source versioning

> **Scope: every Python repository** that uses setuptools as the build backend
> (hatchling-based repos have their own version convention; see
> [Python practices](python.md)). This standard prescribes a single source of
> truth for the version string so that `importlib.metadata.version()`,
> `pkg.__version__`, and `pip show` all agree.

## Rule: one version string, one source

**Rule:** The version string MUST be defined in exactly one place — the
package's `__init__.py` — and read dynamically by the build backend. No other
file may contain a version literal.

**Rationale:** Every duplication is a drift hazard. A version bump in
`pyproject.toml` that misses `__init__.py` (or vice versa) produces silent
inconsistencies: `importlib.metadata.version("mypkg")` returns a different
value than `mypkg.__version__`. Docker tags, CLI output (`--version`), and
logs become unreliable.

> **Failure mode.** A repo that hard-codes `version = "0.3.1"` in both
> `pyproject.toml` and `src/mypkg/__init__.py` appears consistent at first.
> When release-please bumps only `pyproject.toml`, the package reports the new
> version via `importlib.metadata` but `mypkg.__version__` still returns the
> old string — consuming code that inspects `__version__` sees stale data.

## Configuration

### 1. Define `__version__` in the package init

```python
# src/my_package/__init__.py
"""My package."""

__version__ = "0.1.0"
```

The `__version__` string MUST be a plain string literal — no computed values,
no `importlib.metadata` fallbacks, no version-file reads. (The build backend
parses the AST; dynamic expressions are invisible to it.)

### 2. Wire `pyproject.toml` to read it

Replace the static `[project] version` field with a dynamic reference:

```toml
[project]
# Remove: version = "0.1.0"
dynamic = ["version"]

[tool.setuptools.dynamic]
version = {attr = "my_package.__version__"}
```

The `attr` path must match the package's [tool.setuptools.packages.find]
layout. If `packages.find` has `where = ["src"]`, the attribute path is
`my_package.__version__` (not `src.my_package.__version__`).

### 3. Remove any other version literals

Ensure no other file in the repo contains a version string that duplicates
`__init__.py` — in particular, remove `__version__` from `__main__.py`,
`_version.py`, or any other module.

## Interaction with release-please

[Release-please](release-please.md) requires the version to live somewhere it
can read and write. When configured with `release-type: "python"`,
release-please reads the version from the static `[project].version` field in
`pyproject.toml`.

If you use release-please alongside this standard, the version string lives in
`__init__.py` and release-please reads it from `pyproject.toml`. Release-please
writes the bumped version back to `pyproject.toml`'s `[project].version` field.
After a release, copy the new version into `__init__.py` or configure
release-please to write both locations (see release-please docs for
`extra-files` support).

> **Workflow pattern (future):** Once `extra-files` support is confirmed for
> all fleet repos, release-please will update `__init__.py` directly instead of
> `pyproject.toml`, and `pyproject.toml` will use `dynamic = ["version"]` with
> `[tool.setuptools.dynamic]` exclusively. The static `[project].version` field
> remains in `pyproject.toml` today only to satisfy release-please's current
> capabilities.

## Build frontend compatibility

This configuration works with any setuptools-compatible build frontend:
- `pip install -e .`
- `uv pip install -e .`
- `python -m build`

It does NOT work with hatchling, flit, or pdm — each of those backends has its
own dynamic-version mechanism (see [Python practices](python.md) for hatchling
convention).