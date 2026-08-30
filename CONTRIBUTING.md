# Contributing

## Setup

```bash
git clone git@github.com:damien-robotsix/robotsix-standards.git
cd robotsix-standards
uv sync --group dev --group docs
```

## Lint and type-check

```bash
uv run pre-commit run --all-files
uv run mkdocs build --strict
```

## Docs

```bash
uv run mkdocs serve           # http://localhost:8000
uv run mkdocs build --strict  # CI-accurate gate
```

## PR workflow

1. Create a branch, make your change.
2. Run pre-commit (`uv run pre-commit run --all-files`).
3. Run `uv run mkdocs build --strict` — the build gate in CI.
4. Push, open a PR. Every PR is squash-merged to `main`.
5. Use conventional commit subjects (`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`/`test:`/`ci:`) — release-please generates `CHANGELOG.md` from them.

## Code rules

See **[AGENT.md](AGENT.md)** for the repo's canonical working-knowledge rules
for both human contributors and AI agents.
