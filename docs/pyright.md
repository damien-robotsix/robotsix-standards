# Pyright strict mode

> **Scope: every Python repository that runs pyright as a CI gate.** Pyright
> must run at `typeCheckingMode = "strict"` — the same type-safety baseline as
> mypy `--strict` — so the two checkers enforce a consistent gate.

## Why this exists

The fleet's shared `python-ci.yml` workflow runs both mypy and pyright as
separate CI gates. Mypy is configured with `strict = true` (the
[mypy strictness standard](mypy.md)). If pyright is left at its default
`basic` level — no `pyrightconfig.json`, no `.pyrightconfig.json`, no
`[tool.pyright]` section — the two checkers enforce different rulesets.
Pyright passes code that mypy would reject (and vice versa), creating a
divergent safety net where neither gate alone catches every error.

Three mature ASGI/data projects — FastAPI, Pydantic, and Litestar — all run
type-checking at a strict level with no permanent baseline. This standard
extends the fleet's existing mypy strictness posture to pyright so every repo
gets a consistent, matched pair of gates.

## Configuration (mandatory)

Every Python repository that includes pyright in its CI must:

1. **Set `typeCheckingMode = "strict"`** in `pyproject.toml` under
   `[tool.pyright]` (or in a committed `pyrightconfig.json`).  This is the
   single setting that elevates pyright to the same strictness tier as
   mypy `strict = true`.

   ```toml
   [tool.pyright]
   typeCheckingMode = "strict"
   ```

   *Failure prevented:* without this setting, pyright runs at `basic` mode —
   it skips type-checking of unannotated function bodies, tolerates implicit
   `Any`, and reports far fewer issues than mypy `--strict`.  The two checkers
   diverge, and CI's "type-check passed" signal is weaker than it appears.

2. **Keep strict-mode report keys at `"error"`.**  The strict preset enables
   `reportUnknown*`, `reportMatchNotExhaustive`, `reportUnreachable`, and other
   diagnostics as errors.  Do not downgrade these globally.  The set of
   diagnostics pyright strict enables is the closest match to mypy strict's
   coverage.

   *Failure prevented:* downgrading a `reportUnknown*` key to `"warning"` or
   `"none"` weakens the gate for an entire category (e.g. `reportUnknownArgumentType`
   → mypy would catch mismatched argument types but pyright silently passes them).

3. **Use per-diagnostic overrides only for proven-untyped third-party
   dependencies.**  Individual `report_*` keys in `[tool.pyright]` always
   override whatever the strict preset enables.  The only allowed exceptions
   are for modules the repo already exempts in mypy via
   `ignore_missing_imports`:

   ```toml
   [tool.pyright]
   typeCheckingMode = "strict"
   reportMissingTypeStubs = "none"        # untyped deps: cognee, playwright, etc.
   reportMissingImports = "none"          # same set as mypy ignore_missing_imports
   ```

   The set of exemptions must mirror the repo's `[tool.mypy.overrides]` entries
   that set `ignore_missing_imports = true` — not a broader, different set.

   *Failure prevented:* a repo that exempts `cognee.*` in mypy but not in
   pyright gets pyright-only errors for the same untyped dependency — noise
   that either gets suppressed with a blanket `reportMissingTypeStubs = "none"`
   (which hides real gaps) or ignored (which trains the team to skip pyright
   output).  Mirroring the mypy set keeps the suppression surface identical.

## New code

**New modules and packages must pass pyright strict with zero per-file
suppressions beyond the dependency exemptions above.**  A PR that introduces a
new module must not add `# pyright: ignore` comments or per-file diagnostic
overrides to land.

*Failure prevented:* if a new module ships with pyright suppressions for
diagnostics that mypy `--strict` already catches, the module has a type-safety
gap that passed CI because pyright was silenced — the gap is invisible to both
checkers.

## Precedent

| Project | Type checker | Strictness | Gate style |
|---|---|---|---|
| FastAPI | mypy (`strict = true`) | Full strict | Required CI job (`scripts/lint.sh`) |
| Pydantic | pyright | Strict mode | Required CI job (`make typecheck`) |
| Litestar | mypy + pyright | Strict (both) | Separate required CI jobs |

Pydantic — the largest Python project using pyright as its primary type
checker — runs pyright at its strictest level with no baseline and no
permanent suppression list.  Litestar, which runs both mypy and pyright,
enforces strict mode on both with no gap between them.
