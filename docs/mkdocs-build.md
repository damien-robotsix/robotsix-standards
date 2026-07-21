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

## Precedent

- MkDocs ≥ 1.5 release notes recommend the `validation:` block + `--strict`
  for link integrity.
- [MkDocs issue #1570](https://github.com/mkdocs/mkdocs/issues/1570) documents
  why info-level link checks need explicit promotion — they were kept at
  `INFO` for backward compatibility.
- Pydantic and FastAPI both gate docs builds in CI; Pydantic additionally
  uses the post-build autoref hook described above.
