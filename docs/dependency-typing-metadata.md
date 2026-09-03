# Dependency typing metadata

> **Scope: every Python repository.** A package declares the typing status of
> its own runtime dependencies in a `[tool.robotsix.typing]` table in
> `pyproject.toml`, so downstream consumers can generate their mypy and pyright
> exemption lists from an upstream source of truth instead of rediscovering
> `py.typed` status by hand.

## Why this exists

The [mypy strictness](mypy.md) and [pyright strict mode](pyright.md) standards
require every package to run type-checking as a hard CI gate, and both allow a
narrow exemption for **proven-untyped third-party dependencies** — mypy through
`[tool.mypy.overrides]` with `ignore_missing_imports = true`, pyright through
`reportMissingTypeStubs = "none"`. Pyright's standard already requires the two
exemption sets to mirror each other.

But nothing tells a downstream consumer *which* dependencies belong in that set.
Today a consumer must:

1. Install each dependency and inspect it for a `py.typed` marker to learn
   whether it ships inline types.
2. Guess whether an untyped dependency has stubs on typeshed or a separate
   `types-*` distribution.
3. Hand-maintain the mypy and pyright exemption lists with no upstream
   documentation, and re-audit them by hand every time a dependency is bumped.

When a dependency version change adds or removes `py.typed`, the consumer gets
a silent type-checking regression — either new `reportMissingTypeStubs` errors
that were previously suppressed, or a stale `ignore_missing_imports` entry that
`warn_unused_ignores` will (correctly) flag — until someone manually re-checks.

This standard closes the gap: each package publishes the typing status of its
own dependencies as structured data, and downstream tooling reads that data
instead of re-deriving it.

## The declaration (mandatory)

Every Python package **must** declare the typing status of its runtime
dependencies in a `[tool.robotsix.typing]` table in `pyproject.toml`:

```toml
[tool.robotsix.typing]
# Dependencies that ship inline types (a py.typed marker, PEP 561).
typed-dependencies = [
  "httpx >= 0.24",   # py.typed since v0.24
  "pydantic >= 2.0",
]
# Dependencies with no inline types. A trailing comment names the stub
# source (typeshed / a types-* distribution) or states "no types or stubs".
untyped-dependencies = [
  "requests",  # typeshed provides types-requests
  "cognee",    # no types or stubs
]
```

Rules:

1. **Every runtime dependency in `[project.dependencies]` must appear in exactly
   one of the two lists.** A dependency that is neither declared typed nor
   declared untyped is undeclared, and a downstream consumer cannot tell which
   bucket it belongs to.

   *Failure prevented:* an undeclared dependency forces the consumer back to the
   manual install-and-inspect discovery this standard exists to eliminate — the
   declaration is only useful if it is complete.

2. **Each `untyped-dependencies` entry carries a trailing comment naming the
   stub source or its absence** — `# typeshed provides types-<name>`, `#
   stubs: <name>-stubs`, or `# no types or stubs`.

   *Failure prevented:* "untyped" alone does not tell the consumer whether to
   add a `types-*` dev dependency (stubs exist) or to add an
   `ignore_missing_imports` exemption (no stubs anywhere). The comment is the
   difference between a fixable gap and a permanent one.

3. **Pin the version boundary at which typing status holds** for `typed`
   entries whose `py.typed` status changed at a known release (e.g.
   `httpx >= 0.24`). Where a dependency has always shipped types, the bare name
   is sufficient.

   *Failure prevented:* without the boundary, a resolver that pulls an older
   pre-`py.typed` release silently drops the dependency's types and the
   consumer's exemption list no longer matches reality.

## Maintainer obligations

The declaration is only trustworthy if it stays in step with the dependency
set. A package maintainer **must**:

- **Add an entry when adding a runtime dependency.** The same PR that adds a
  line to `[project.dependencies]` adds the matching `typed`/`untyped` entry —
  never in a follow-up.
- **Move an entry when a dependency's typing status changes.** When a bump
  crosses the release where a dependency added (or dropped) `py.typed`, move it
  between the two lists and update the version boundary and comment.
- **Remove an entry when removing the dependency**, so the declaration never
  lists a dependency the package no longer uses.

*Failure prevented:* a declaration that drifts from `[project.dependencies]` is
worse than none — a consumer that trusts a stale list ships exemptions for
dependencies that are gone and misses exemptions for ones that were added.

## Downstream consumption

Downstream consumers generate their mypy `[tool.mypy.overrides]` and pyright
`reportMissingTypeStubs` exemptions from the upstream `untyped-dependencies`
declarations rather than curating them by hand. The exemption set a consumer
derives this way is exactly the mirrored mypy/pyright set the
[pyright strict mode](pyright.md) standard already requires — this standard
supplies its upstream source of truth.

A fleet-wide helper reads the `[tool.robotsix.typing]` tables of a repo's
first-party dependencies and emits the exemption stanzas; consumers run it
instead of maintaining the lists manually, so a dependency bump that changes a
typing status updates the exemptions from the upstream declaration in the same
step.

## Precedent

FastAPI, Pydantic, and Litestar — the projects cited in the
[mypy](mypy.md#precedent) and [pyright](pyright.md#precedent) standards — keep
strict type-checking green in CI by curating, out of band, which dependencies
are typed and which need stubs. That knowledge lives in maintainers' heads and
their CI config, not in a machine-readable form a downstream consumer can read.
`[tool.robotsix.typing]` makes the same knowledge explicit and consumable, so
the fleet does not re-derive it once per consuming repo.

## Companion standards

- **[Mypy strictness](mypy.md)** — the mypy gate and its
  `ignore_missing_imports` exemption for untyped dependencies.
- **[Pyright strict mode](pyright.md)** — the matching pyright gate; its
  `reportMissingTypeStubs` exemption set must mirror mypy's, and both are
  generated from the `untyped-dependencies` declaration above.
- **[Python practices](python.md#packaging)** — the `py.typed` marker and
  `Typing :: Typed` classifier every first-party package must ship, which is
  what makes a first-party dependency `typed` in this declaration.
