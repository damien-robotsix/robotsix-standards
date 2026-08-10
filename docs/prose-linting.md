# Prose linting

> **Scope: every repository that publishes MkDocs documentation.**
> Repos without MkDocs (content-only repos, ROS 2 workspaces, deployment-only
> repos) are exempt.

## Why this exists

[Markdown linting](markdown-linting.md) catches syntax, heading, and spelling
errors — but it does not enforce prose style. Without an automated prose gate,
passive voice, weasel words, non-inclusive terminology, and misspelled product
names accumulate silently across the fleet's documentation sites. Reviewers
read for meaning, not for readability metrics or fleet-specific vocabulary —
the drift is only noticed when a human happens to spot it, and by then the
same term is often misspelled in a dozen pages.

[Vale](https://vale.sh/) (MIT-licensed, `github.com/errata-ai/vale`) fills
this gap. It is a declarative prose linter that checks for style, readability,
and vocabulary consistency — and it integrates into the fleet's existing
pre-commit + CI pipeline with no separate workflow.

## Pre-commit hooks

Add both hooks to `.pre-commit-config.yaml`. The `sync` hook fetches bundled
styles (no separate install); the lint hook runs on every Markdown file.

```yaml
  - repo: https://github.com/errata-ai/vale
    rev: v3.15.1
    hooks:
      - id: vale
        name: vale sync
        pass_filenames: false
        args: [sync]
      - id: vale
        args: [--output=line, --minAlertLevel=error]
```

**Failure mode prevented:** docs-sites that pass `mkdocs build --strict` but
ship with passive-voice walls, filler phrases ("easily", "just", "simply"),
outdated terminology, and misspelled fleet product names — all of which
degrade the reader's trust and the fleet's professional surface.

## Configuration

### `.vale.ini` at repo root

```ini
StylesPath = styles
MinAlertLevel = error
Vocab = robotsix
Packages = errata-ai/write-good
[*.md]
BasedOnStyles = write-good
```

**The `StylesPath` directory (`styles/`) is gitignored** — `vale sync`
regenerates it from the declared packages. Only the vocabulary files
(in `styles/config/vocabularies/`) are version-controlled.

### Fleet vocabulary

Create `styles/config/vocabularies/robotsix/` with two files:

#### `accept.txt` — fleet-specific terms that Vale should not flag

```text
robotsix
towncrier
central-deploy
langfuse
llmio
semgrep
trufflehog
dependabot
mkdocs
mkdocstrings
codespell
hadolint
actionlint
ruff
mypy
deptry
pydantic
hatchling
pre-commit
pypi
cyclonedx
sbom
trivy
scorecard
OpenSSF
OWASP
SLSA
Sigstore
backend
frontend
websocket
lifecycle
onboarding
cutover
supersession
```

Each term is a fleet product, tool, or framework name that spell-check and
style rules would otherwise flag as errors. Adding them here suppresses the
false positive across every doc page in the repo.

#### `reject.txt` — terms that must never appear in fleet documentation

```text
whitelist
blacklist
master/slave
sanity.check
crazy
```

These terms have well-established inclusive replacements (`allowlist`,
`blocklist`, `primary`/`replica`, `consistency check`, `placeholder`). Vale
flags every occurrence so they are caught before review.

## CI integration

No separate workflow is needed — `pre-commit run --all-files` executes Vale
as part of the standard pre-commit CI gate (see
[Pre-commit baseline](pre-commit-baseline.md)). The `sync` hook runs first
to pull the bundled styles, then the lint hook checks all Markdown files
at the `error` severity level.

## Fleet precedent

- Major Python OSS documentation projects (including `pydantic/pydantic` and
  `encode/httpx`) use Vale for prose consistency — the same declarative
  style-checking pattern, integrated through pre-commit.
- The fleet's own [Markdown linting](markdown-linting.md) standard already
  acknowledges the prose-style gap — this standard fills it with an OSS tool
  that slots into the existing pre-commit + CI pipeline.
