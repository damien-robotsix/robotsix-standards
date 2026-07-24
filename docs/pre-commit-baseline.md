# Pre-commit baseline

> **Scope: every Python repository.** These are the file-hygiene hooks every
> Python repo runs at commit time — language-agnostic checks that complement
> the code-quality hooks documented in [Python practices](python.md#pre-commit-hooks).

Every Python repo's `.pre-commit-config.yaml` includes a baseline of hooks
from [`pre-commit/pre-commit-hooks`](https://github.com/pre-commit/pre-commit-hooks)
that catch common hygiene failures before they reach CI or the commit log.
These hooks have no language runtime, run in milliseconds, and require zero
configuration for Python repos.

## Hooks

The baseline is five hooks from the official `pre-commit/pre-commit-hooks`
repo, each endorsed as "universally recommended" or "strongly recommended" by
the project itself:

```yaml
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-toml
      - id: check-added-large-files
```

### trailing-whitespace

Removes trailing whitespace from every line. Without this, editors with
`trim_trailing_whitespace` off produce noisy diffs that obscure the real
change. The hook fixes the file in place — no manual cleanup needed.

**Failure mode prevented:** commits carry trailing-whitespace-only lines that
pollute diffs, waste reviewer attention, and create merge-conflict noise.

### end-of-file-fixer

Ensures every file ends with exactly one newline, and trims extra trailing
newlines. POSIX tools (and GitHub's diff viewer) behave poorly when the final
newline is missing — `\ No newline at end of file` annotations clutter diffs.

**Failure mode prevented:** missing-final-newline annotations in GitHub diffs
and inconsistent EOF handling across editors and tooling.

### check-yaml

Parses every `.yml` and `.yaml` file (recursively) and fails on invalid YAML
syntax. Catches indentation errors, duplicated keys, and tab characters before
they reach CI or deploy.

**Failure mode prevented:** broken CI workflows, invalid `docker-compose.yml`
files, and unparsable config that fails at runtime rather than at commit time.

### check-toml

Parses every `.toml` file (recursively) and fails on invalid TOML syntax.
Python repos use TOML for `pyproject.toml`; a stray unescaped character can
silently break a build or publish.

**Failure mode prevented:** broken `pyproject.toml` that prevents `uv sync`,
`pip install`, or PyPI publishing — detected at commit time instead of in CI.

### check-added-large-files

Fails if a staged file exceeds 750 KB (the default threshold). Large binaries
accidentally committed bloat the repo forever (Git stores them in every clone
forever). The hook can be overridden per-file with `--enforce-all` or a
`.pre-commit-config.yaml` `exclude` pattern for intentional exceptions (e.g.
test fixtures).

**Failure mode prevented:** accidental commits of large binaries (logs, dumps,
datasets, model weights) that permanently inflate the repo and slow every
clone.

## Relationship to the full hook set

These five hooks are a **subset** of the standard pre-commit configuration
defined in [Python practices](python.md#pre-commit-hooks). That page documents
the full fleet-standard set — including `ruff`, `mypy`, `detect-secrets`,
`actionlint`, `vulture`, and the content-only-repo subset. This page isolates
the **file-hygiene baseline** so repos that are not yet at the full standard
can adopt a minimal, uncontroversial starting point that catches the most
common commit-time mistakes.

The `rev` field follows the fleet pinning rule: a tagged release, bumped
deliberately when the fleet standard updates, never floating (`main` or
`latest`).
