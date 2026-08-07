# Module taxonomy scope

> **Scope: every repository with a `docs/modules.yaml`.**
> This page defines *what belongs in the taxonomy*. For the file's structure and
> keys, see the [robotsix-modules schema
> reference](https://github.com/damien-robotsix/robotsix-modules/blob/main/docs/schema-reference.md).

## Why this exists

A module taxonomy is an inventory of a repository's **logical modules** — what
they are, which files they own, and how they depend on one another. It answers
questions like *"what does the `lifecycle` module consist of?"* and *"what
breaks if I change `protocol`?"*.

`check-registration` originally required **every tracked file** to be claimed by
some module. That sounds like rigour, and it is not: it forces files that are
not modules — and have no dependency relationships — to be filed under one
anyway, purely to satisfy a completeness count.

Measured on the fleet in August 2026, before this rule existed:

| repo | tracked files | of which repo operation |
|---|---|---|
| robotsix-central-deploy | 658 | **404 (61%)** |
| robotsix-agent-comm | — | 43 unclassified, 32 of them scaffolding |

So most of a taxonomy described something other than modules. And because
towncrier writes **one fragment file per pull request**, every changelog entry
became a taxonomy edit — which is how *"register this fragment in
`docs/modules.yaml`"* became a recurring ticket class. One such ticket sat
blocked for a week; its branch proposed **199** explicit fragment entries.

## Rules

### 1. The taxonomy covers product code, not repo operation

**Rule:** A file belongs in the taxonomy when it describes **what the software
does**. A file describing how the repository is built, linted, packaged,
documented, released or deployed is *repo operation* and is exempt.

In practice that means `src/`, `tests/` and prose documentation are claimed;
almost nothing else is.

| Claimed | Exempt (repo operation) |
|---|---|
| `src/**`, `tests/**` | `.github/**`, CI workflows |
| `docs/*.md` prose | `pyproject.toml`, `uv.lock`, `package.json` |
| runtime assets (templates, static CSS/JS) | `Dockerfile`, `docker-compose*.yml`, `Makefile` |
| | linter/formatter config, `mkdocs.yml`, `codecov.yml` |
| | `changelog.d/**`, `CHANGELOG.md`, `LICENSE`, `README.md` |

**Rationale:** The dividing line is *purpose*, not file type. `.markdownlint.json`
is not a logical module: it has no dependencies on other modules, and nothing
about it informs drift detection or dead-code analysis. Claiming it adds an
entry that must be maintained and tells no reader anything.

> **Failure mode prevented.** A repo enumerates every changelog fragment in
> `docs/modules.yaml`. Each PR then needs a second, unrelated edit; the
> enumeration drifts; and eventually someone writes a ticket to "register the
> fragments", which is a ticket about the taxonomy's own bookkeeping rather than
> about the software.

### 2. Exemption is the tool's default — do not re-claim scaffolding

**Rule:** `robotsix-modules` ships `DEFAULT_EXCLUDED_PATHS` covering the exempt
column above. Repos must **not** add module `paths` entries for those files, and
must not work around the check with a catch-all glob such as
`changelog.d/*.md`.

**Rationale:** Before the defaults existed, every repo independently invented
the same glob workaround. A workaround repeated in seven repos is a missing
feature, and muting the check per-repo hides the same category error in a
different place.

Claiming an exempt file is *legal* — the exemption relaxes the requirement to
claim, it does not forbid it — so migration is gradual and nothing breaks. But
new taxonomies should not do it.

### 3. Repo-specific exemptions go in `excluded_paths`

**Rule:** A repo with scaffolding the defaults do not cover declares it
explicitly:

```yaml
excluded_paths:
  - "templates/**"   # scaffold sources for generated projects, not this package
```

`excluded_paths` **replaces** the defaults rather than extending them, so a repo
that sets it must restate any defaults it still wants. An empty list restores
full coverage for a repo that genuinely wants every file claimed.

**Rationale:** Making it a replacement rather than a merge keeps the effective
set readable in one place. The cost is verbosity in the rare repo that needs it,
which is the right trade against an exemption list assembled from two sources.

> **Failure mode prevented.** A repo vendors a template tree whose files look
> like source (`templates/python-package/src/...`) but belong to no module in
> *this* package. Without an explicit exemption those files are permanently
> unclassified, so the check is either red forever or switched off entirely.

### 4. Unclassified `src/` or `tests/` files are real findings

**Rule:** After exemptions, any remaining `unclassified_file` finding must be
resolved by claiming the file — never by widening the exemptions.

**Rationale:** This is the signal the check exists to produce. Once scaffolding
stopped drowning it, the August 2026 fleet audit surfaced genuinely unowned
source in four repos, including three CSS files under
`src/robotsix_auto_mail/server/static/` that had been invisible among 404
scaffolding entries.

> **Failure mode prevented.** A module is renamed and its files are silently
> orphaned. With a noisy check nobody reads the output; with a quiet one, the
> orphan is the only line printed.

## Verifying a repo

```bash
robotsix-modules check-registration docs/modules.yaml
```

Exit 0 means every non-exempt file is claimed exactly once. Findings name the
file and the kind (`unclassified_file`, `stale_path`, `duplicate_registration`).

A taxonomy that fails to parse — for example a module entry missing its `id` —
reports a schema error rather than a finding. Validate structure separately:

```bash
robotsix-modules validate docs/modules.yaml
```
