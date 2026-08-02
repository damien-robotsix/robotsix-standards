# MkDocs build integrity

> **Scope: every repository that publishes an MkDocs documentation site.**
> Repos without MkDocs (content-only repos, ROS 2 workspaces, deployment-only
> repos) are exempt.

## Why this exists

MkDocs is the fleet's documentation engine (Material theme, mkdocstrings).
Without a strict build gate, broken internal links, missing nav pages,
unresolved anchors, and malformed frontmatter silently degrade the published
site. The two rules below catch every class of build-time error MkDocs can
surface.

## Rules

### 1. Build with `--strict`

In CI, the docs build command must be `uv run --group docs mkdocs build
--strict`. The `--strict` flag promotes MkDocs warnings (missing nav pages,
unresolved template variables, broken `extra_javascript` / `extra_css`
paths, malformed frontmatter) to hard errors — so a broken link fails CI, not
just the published site.

Setting `strict: true` in `mkdocs.yml` achieves the same effect and is
preferred when the build command is not under the repo's direct control
(e.g. called by a shared reusable workflow that doesn't accept extra CLI
flags).  Both forms are acceptable — the requirement is that the build fails
on warnings, not *how* the flag is delivered.

**Failure mode prevented:** a PR adds a page but forgets to register it in
`mkdocs.yml`'s `nav`. Without `--strict`, MkDocs emits a single log line at
`WARNING` level, CI passes, and the page is invisible on the published site
— broken navigation the author and reviewer never see.

The shared `python-docs.yml` reusable workflow in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
runs `mkdocs build --strict` by default — repos that call the shared workflow
get this gate automatically.

### 2. Add a `validation:` block to `mkdocs.yml`

The most important link checks default to *info* level in MkDocs (≥ 1.5) and
are **not** promoted by `--strict` alone. A `validation:` block raises them
to `warn`, where `--strict` then promotes them to errors:

```yaml
validation:
  nav:
    not_found: warn
    omitted_files: info
  links:
    not_found: warn
    anchors: warn
    absolute_links: warn
    unrecognized_links: warn
```

| Key | What it catches |
|---|---|
| `nav.not_found` | A page listed in `nav` that doesn't exist on disk |
| `nav.omitted_files` | A `.md` file on disk that isn't in the `nav` (info; noise in large repos) |
| `links.not_found` | A cross-page markdown link whose target `.md` file doesn't exist |
| `links.anchors` | A link to a heading anchor (`#some-heading`) that doesn't exist on the target page |
| `links.absolute_links` | An absolute URL that should probably be relative |
| `links.unrecognized_links` | A link MkDocs can't classify — often a typo or a bare fragment |

**Failure mode prevented:** a PR renames a heading but the cross-page links
pointing to it still reference the old anchor. Without the `validation:`
block, MkDocs logs at `INFO` level, `--strict` doesn't see it, and the
published site has dead anchor links.

## What `--strict` does **not** catch

`--strict` and the `validation:` block together cover every warning MkDocs
itself can surface, but they do **not** catch broken **mkdocstrings
cross-references** (unresolved `autorefs`). The `autorefs` plugin emits
warnings through Python's logging, which MkDocs does not treat as build
warnings. Pydantic addresses this with a custom post-build hook
([pydantic/pydantic#10203](https://github.com/pydantic/pydantic/pull/10203)).
This standard does **not** require that hook — it is an optional add-on for
repos that want autoref integrity. The convention here is: ship the hook if
`autorefs` drift has bitten you, but don't gate on it fleet-wide until the
pattern is proven in more than one repo.

### 3. Surface the changelog in the docs nav

Every repo that publishes an MkDocs docs site and maintains a root
`CHANGELOG.md` must include it in the docs `nav` so it is discoverable to
users browsing the published site. A changelog that lives only in the repo
root is invisible to readers of the docs.

```yaml
nav:
  - Changelog: CHANGELOG.md
```

**Mechanics.** The root `CHANGELOG.md` is outside `docs_dir` by default and
won't resolve. The repo must make it resolvable *without* committing a
duplicate copy into `docs/`. Two patterns are acceptable:

| Pattern | How |
|---|---|
| **Symlink** | `ln -s ../CHANGELOG.md docs/CHANGELOG.md`. Git tracks the symlink as a file — every clone and CI run resolves it. Simple, zero-build-step. |
| **Build-time copy** | An `on_pre_build` MkDocs hook that copies `CHANGELOG.md` into `docs/` before the site builds. Preferable when the target platform does not support symlinks (Windows CI runners without Developer Mode). |

Either way, the file referenced in `nav` must be the canonical root
`CHANGELOG.md` — not a manually-maintained copy that can drift.

**Failure mode prevented:** a repo has a well-maintained changelog (towncrier,
Keep a Changelog format) but users browsing the docs site never see it because
it isn't in the nav. Release notes that require navigating away from the docs
to the GitHub repo are functionally hidden from most readers.

### 4. Register new pages in the same change

When a new standards page is added, it must be registered in the
`mkdocs.yml` `nav` in the **same** change that adds the page.  Adding a
`README.md` or `docs/index.md` TOC entry alone leaves the page unbuilt by
MkDocs and requires a second rework ticket — the TOC-sync gate is
one-directional (it checks that TOC entries match existing files but does
**not** check that every file has a nav entry).

**Failure mode prevented:** a PR adds a new standards page and its
`README.md` / `docs/index.md` TOC entries correctly, passes the TOC-sync CI
gate, and merges — but the page is invisible on the published docs site
because it was never wired into the MkDocs `nav`.  The author and reviewer
both assumed the TOC-sync gate covered nav registration; it doesn't.

### 5. Run a rendered-HTML link checker in a separate CI job

`--strict` and the `validation:` block catch broken internal links at build
time, but they do **not** verify that external URLs are still reachable or
that every internal anchor on the rendered HTML page resolves.  A separate
rendered-HTML link checker — run against the built `site/` directory —
validates every hyperlink on the published page: internal anchors,
cross-page links, and external URLs.

Two tools are acceptable.  Both satisfy the rule — choose the one that fits
the repo's tolerance for external-URL flakiness:

**`mkdocs-htmlproofer-plugin` (build-time, internal + external).**
A MkDocs plugin that validates the rendered HTML during `mkdocs build`.
Internal link and anchor failures should be hard errors (`raise_error_after_finish:
true`).  External URLs that are known to be flaky or rate-limited (GitHub,
raw.githubusercontent.com, docs.github.com) should be excluded via
`ignore_urls` so the build remains deterministic:

```yaml
plugins:
  - htmlproofer:
      raise_error_after_finish: true
      ignore_urls:
        - "http://localhost*"
        - "https://raw.githubusercontent.com/*"
        - "https://github.com/*"
        - "https://docs.github.com/*"
```

**`lychee` (post-build, separate job).**  A standalone Rust link checker
(`lycheeverse/lychee-action`) that validates the `site/` directory.  Run it
in a **separate CI job** from the build-and-deploy job so a flaky external
URL cannot block the deploy itself:

```yaml
linkcheck:
  runs-on: ubuntu-24.04
  steps:
    - uses: actions/checkout@v4
    - # … build the docs into site/ …
    - uses: lycheeverse/lychee-action@v2
      with:
        fail: true
        args: >-
          --accept 200,206,403,429,503
          --exclude-private
          --cache
          site/
```

**Separation principle.**  The link-check job must be a distinct CI job from
the build-and-deploy job (or at least a distinct step whose failure does not
block deploy).  The deploy path must never be gated on external URL
reachability — a third-party site going down should not block a docs deploy.
The link-check job gates **pull requests** (blocking merge when links are
broken) but is non-blocking on the deploy workflow so a transient upstream
outage never prevents publishing.

**PR-time gating.**  Every link-validation mechanism — `--strict`, the
`validation:` block, and the rendered-HTML link checker — must run on pull
requests, not only at deploy.  A gate that only fires on `push` to `main`
(or on a `workflow_dispatch` deploy) catches breakage after it reaches
readers.  The shared `python-docs.yml` reusable workflow already runs
`mkdocs build --strict` on PRs; the rendered-HTML link checker must also be
wired into the PR workflow (as a separate job or step).

**Failure mode prevented:** a PR links to an external resource (a blog post,
a package page, an RFC) that later moves or goes offline.  Without a
rendered-HTML link checker, the dead link is invisible — the build passes,
the `validation:` block only checks internal structure, and readers encounter
a 404 with no warning.  The link-check job catches this at PR time, before
the dead link reaches readers.  A further failure mode: a flaky external URL
blocks the docs deploy pipeline, preventing the site from updating even
though the broken link is on a third-party domain the repo does not control.
Separating the link-check job from deploy prevents this.

## Precedent

- [Pydantic](https://github.com/pydantic/pydantic),
  [FastAPI](https://github.com/fastapi/fastapi), and
  [SQLModel](https://github.com/fastapi/sqlmodel) all surface their root
  `CHANGELOG.md` as a docs nav page via a `docs/`-tree copy or symlink.
  MkDocs-material has no built-in changelog plugin; this nav entry plus a
  resolution mechanism is the established convention.
- MkDocs ≥ 1.5 release notes recommend the `validation:` block + `--strict`
  for link integrity.
- [MkDocs issue #1570](https://github.com/mkdocs/mkdocs/issues/1570) documents
  why info-level link checks need explicit promotion — they were kept at
  `INFO` for backward compatibility.
- Pydantic and FastAPI both gate docs builds in CI; Pydantic additionally
  uses the post-build autoref hook described above.
