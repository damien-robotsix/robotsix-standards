# Markdown linting

> **Scope: every Python repository that publishes MkDocs documentation.**
> Repos without MkDocs (content-only repos, ROS 2 workspaces, deployment-only
> repos) are exempt.

## Why this exists

Without automated Markdown quality gates, each repo's documentation drifts
independently: broken internal links, inconsistent heading styles, spelling
errors, and deprecated inline-HTML patterns accumulate over time. The
fleet publishes docs sites with `mkdocs build --strict` (see
[MkDocs build integrity](mkdocs-build.md)), which catches structural MkDocs
errors but does not enforce prose style, heading consistency, or spelling —
those gaps are filled by the two hooks below.

## Pre-commit hooks

Add both hooks to `.pre-commit-config.yaml`. The `markdownlint-cli2` hook
runs on every `.md` file; `codespell` runs across the entire repo.

### `markdownlint-cli2` — Markdown style enforcement

```yaml
  - repo: https://github.com/DavidAnson/markdownlint-cli2
    rev: v0.17.2
    hooks:
      - id: markdownlint-cli2
        args: ["#fix"]
```

**The `#fix` arg is optional.** When present it auto-fixes fixable violations
on commit. Remove it if you prefer to fix manually — the CI job still runs
the check and fails on any violation.

### `codespell` — spell-checking for prose

```yaml
  - repo: https://github.com/codespell-project/codespell
    rev: v2.4.1
    hooks:
      - id: codespell
        args: ["--ignore-words-list", "hist,ist,te,nd", "--skip", "*.lock,uv.lock,*.css,*.map,*.min.*,.git/,node_modules/,site/,vendor/"]
```

**Failure mode prevented:** misspelled words in documentation and comments
that survive review because reviewers read for meaning, not spelling.

## Recommended config files

### `.markdownlint-cli2.yaml`

Create this file at the repo root:

```yaml
# .markdownlint-cli2.yaml
default: true

MD013:
  line_length: 120
  code_blocks: false      # long code lines in docs
  tables: false           # table cells exceed line length

MD024:
  allow_different_nesting: true   # repeated headings under different parents

MD033: false              # inline HTML for mkdocs-material admonitions, image sizing

MD041: false              # docs pages start with frontmatter, not H1

MD046:
  style: "fenced"         # enforce fenced code blocks, not indented
```

Each rule override states the failure it prevents:

- **MD013 (line length):** code blocks and tables routinely exceed 80 or 120
  characters; silencing them avoids noise without losing heading/paragraph
  line-length enforcement.
- **MD024 (duplicate headings):** MkDocs generates anchor slugs from heading
  text; identical headings under different parent sections are valid and
  common (e.g. "Usage" under both "CLI" and "Library").
- **MD033 (no inline HTML):** mkdocs-material admonitions (`!!! note`) and
  image-sizing attributes require inline HTML; a blanket ban breaks the
  theme.
- **MD041 (first line is H1):** docs pages in MkDocs Material repos
  frequently start with YAML frontmatter (`---`), not an H1.
- **MD046 (code block style):** fenced blocks (`` ``` ``) are the fleet
  convention; indented blocks are ambiguous with list items.

### `[tool.codespell]` in `pyproject.toml`

```toml
[tool.codespell]
skip = "*.lock,*.css,*.map,*.min.*,.git/,node_modules/,uv.lock,LICENSE,site/,vendor/"
ignore-words-list = "hist,ist,te,nd"
check-filenames = true
```

**Failure mode prevented:** `codespell` without skip patterns scans lock
files, minified JS/CSS, and vendored code — producing false-positive noise
that trains contributors to ignore the hook.

## Fleet precedent

- **pydantic/pydantic** (the leading Python validation library in the
  FastAPI ecosystem) uses both `markdownlint-cli2` and `codespell` in its
  `.pre-commit-config.yaml` — this is a proven, battle-tested combination.
- The ROS 2 fleet already runs `markdownlint` and `codespell` via a justfile;
  this standard brings the same gates to every Python repo via the shared
  pre-commit mechanism (see [ROS 2 practices](ros2.md) for the ROS 2
  fleet's equivalent).
