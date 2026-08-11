# Contributor guide in docs nav

> **Scope: every repository that publishes an MkDocs documentation site and
> maintains a root `CONTRIBUTING.md`.**
> Repos without MkDocs (content-only repos, ROS 2 workspaces, deployment-only
> repos) are exempt, as are repos without a contributor guide.

## Why this exists

A root `CONTRIBUTING.md` is GitHub's standard for contributor-facing
documentation — it renders on the repo's landing page and is linked from
issue and PR templates. But when a repo also publishes an MkDocs documentation
site, that same contributor guide must be reachable from the docs nav so that
readers who land on the published site can find it without navigating away to
GitHub.

## Rules

### 1. Surface the contributor guide in the docs nav

Every repo that publishes an MkDocs docs site and maintains a root
`CONTRIBUTING.md` must include it in the docs `nav` so it is discoverable to
readers browsing the published site. A contributor guide that lives only in
the repo root is invisible to readers of the docs.

```yaml
nav:
  - Contributing: contributing.md
```

**Title.** Use **Contributing** or **Development** as the nav label — either
is acceptable. The requirement is that the guide is in the nav, not the exact
wording.

**Failure mode prevented:** a repo has a thorough contributor guide in its
root `CONTRIBUTING.md`, visible on GitHub, but contributors who discover the
repo through its published docs site never see it — the guide is functionally
invisible to that audience.

### 2. Single source of truth

The nav entry must resolve to the canonical root `CONTRIBUTING.md` — not a
manually-maintained copy that can drift. Two patterns are acceptable:

| Pattern | How |
|---|---|
| **Include plugin** | Install `mkdocs-include-markdown-plugin` and create a stub `docs/contributing.md` containing `{! ../CONTRIBUTING.md !}`. The include directive pulls the root file into the page at build time — the root file remains the single source of truth, and the stub is a build artifact that never needs manual upkeep. |
| **Symlink** | `ln -s ../CONTRIBUTING.md docs/contributing.md`. Git tracks the symlink as a file — every clone and CI run resolves it. Simple, zero-build-step, zero-plugin. Preferred when the target platform supports symlinks (Linux/macOS CI runners). |

**Failure mode prevented:** a contributor updates `CONTRIBUTING.md` in the
repo root but the copy in `docs/` is stale because it was manually duplicated
rather than linked or included. The published docs site shows outdated
contributor guidance, and the reviewer who merges the PR sees a green build
with no warning.

### 3. Link from the home page

The docs home page (`docs/index.md`) or landing README must link to the
contributor guide so it is discoverable without navigating the nav sidebar.
This is satisfied by a paragraph or bullet in the home page pointing to the
contributor guide, e.g.:

```markdown
See the [Contributing guide](contributing.md) for how to set up a development
environment and submit changes.
```

**Failure mode prevented:** a reader lands on the docs home page, sees no
contributor link, and assumes the project has no contributor guide — even
though one exists in the nav sidebar. The home-page link is a second
discovery path that catches readers who don't expand the sidebar.

## Precedent

- [FastAPI](https://fastapi.tiangolo.com/contributing/) surfaces its
  contributor guide as a docs nav page under "Development - Contributing".
- [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/contributing/)
  includes contributing guidance in its published documentation.
- MkDocs provides `validation.nav` + `--strict` to catch nav↔file drift
  (see [MkDocs build integrity](mkdocs-build.md)), but these do not enforce
  that contributing content is in the site at all — so the convention must
  be codified as a standard.
