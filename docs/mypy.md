# Mypy strictness as a hard CI gate

> **Scope: every Python repository.** Static type-checking runs as a CI gate
> (not advisory), new code must be type-clean under strict mode, and baseline
> snapshots are a bootstrapping scaffold with a defined exit path — never a
> permanent suppression list.

## Why this exists

The fleet's shared python-ci template exposes a `mypy-advisory` input. When
set to `true`, mypy runs in advisory mode: it reports errors but never fails
the pipeline. A repo that ships with a nonzero strict-mode error baseline and
`mypy-advisory: true` can accumulate new type errors indefinitely with no CI
signal — the gate is effectively absent.

Three mature ASGI/data projects — FastAPI, Pydantic, and Litestar — all gate
on type-checking as a required CI job. FastAPI runs `uv run mypy fastapi` in
`scripts/lint.sh` with `strict = true`; a single mypy error fails the
pipeline. None of them ship a permanent baseline snapshot as the long-term
enforcement strategy.

This standard defines the fleet-wide convention: mypy is a gate, not a
whisper; baseline snapshots shrink monotonically and are eventually deleted;
and new or migrated code must be type-clean under strict mode from day one.

## Baseline requirements (mandatory)

Every Python repository **must**:

1. **Run mypy as a CI gate, not advisory.** The shared python-ci template
   `mypy-advisory` input must be `false` (or absent, defaulting to `false`)
   so a new or growing type-error count fails the pipeline.

   *Failure prevented:* a repo that ships with `mypy-advisory: true` has no
   automated signal when new type errors are introduced — the baseline can
   grow without bound and the first a team learns of a type-level regression
   is a runtime `AttributeError` or `TypeError` in production.

2. **Adopt `strict = true` (or an equivalent opt-in set) in mypy
   configuration.** The canonical path is a `[tool.mypy]` table in
   `pyproject.toml` with `strict = true`. Repos that cannot enable every
   strict-mode check at once may opt in individual flags (`check_untyped_defs`,
   `disallow_any_generics`, `no_implicit_optional`, `warn_unused_ignores`,
   etc.) as stepping stones toward `strict = true`.

   *Failure prevented:* without strict mode, mypy silently skips untyped
   function bodies, tolerates implicit `Any`, and misses whole categories of
   soundness errors — the type-checker runs but the coverage gap is invisible.

3. **Require `warn_unused_ignores = true`** (implied by `strict = true`).
   Every `# type: ignore[<code>]` suppression must target a specific error
   code; stale ignores become CI failures.

   *Failure prevented:* a blanket `# type: ignore` without an error code
   suppresses every mypy error on that line, including new ones introduced by
   a dependency upgrade or refactor. With `warn_unused_ignores`, a
   once-necessary suppression that becomes stale is flagged and removed.

## Baseline bootstrapping (transitional scaffold)

A repo that currently has a nonzero type-error count under strict mode may
use `mypy-baseline` as a **bootstrapping scaffold with a defined exit**,
never as a permanent state:

1. **Capture the current baseline once** with
   `uv run mypy-baseline --write-baseline` to produce a
   `mypy-baseline.txt` snapshot.

2. **Gate on baseline stability.** CI runs
   `uv run mypy-baseline --check` (or equivalent); a diff that introduces
   new type errors fails the pipeline. This is the minimum viable gate —
   no new errors, even while the legacy baseline exists.

   *Failure prevented:* without a stability gate, new type errors blend
   into the baseline snapshot and are invisible until the next manual
   re-capture — the baseline becomes a permanent suppression list rather
   than a shrinking todo list.

3. **Define a monotonic-shrink trajectory.** Each repo documents which
   error class it is clearing next (e.g. "clear all `[arg-type]` errors
   first, then `[union-attr]`") and periodically re-captures the baseline
   (`mypy-baseline --write-baseline`) to reflect the shrinking count.

4. **Delete the baseline entirely when it reaches zero entries.** At that
   point CI gates on `uv run mypy .` directly — a plain, hard gate with no
   snapshot.

   *Failure prevented:* a baseline snapshot that is never re-captured and
   never shrunk becomes a permanent suppression list — the repo runs mypy
   but gets none of the safety benefit, and the snapshot drifts from the
   actual error set.

## New and migrated code

**New modules, packages, and subsystems added to a repo must be type-clean
under strict mode with zero baseline entries.** A PR that introduces a new
module must not add entries to `mypy-baseline.txt` for that module.

**A repo migrating from untyped to typed code must add type annotations
before or in the same PR as the code change.** If a PR touches a previously
untyped function, it must annotate that function — or, at minimum, not
worsen the existing baseline.

*Failure prevented:* if new code is allowed to land untyped under a baseline
snapshot, the baseline never shrinks — every new module adds suppression
entries, and the repo accumulates permanent type debt rather than converging
on type-clean.

## Precedent

| Project | Type checker | Gate style | Baseline? |
|---|---|---|---|
| FastAPI | mypy (`strict = true`) | Required CI job (`scripts/lint.sh`) | None — clean run from day one |
| Pydantic | pyright | Required CI job (`make typecheck`) | None |
| Litestar | mypy + pyright | Separate required CI jobs | None |

None of the surveyed projects ship a permanent `mypy-baseline.txt` snapshot
as the long-term enforcement strategy. Where the `mypy-baseline` tool
appears in the ecosystem, its own documentation treats the snapshot as a
bootstrapping scaffold: shrink periodically, delete, then gate on the raw
type-checker.

## Companion standards

- **[Pyright strict mode](pyright.md)** — the matching pyright strictness
  standard.  Every fleet repo that runs both mypy and pyright in CI must
  configure pyright with `typeCheckingMode = "strict"` so the two checkers
  enforce a consistent gate.
