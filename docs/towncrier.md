# Towncrier changelog management

> **Scope: every Python repository.** Towncrier is the fleet-wide changelog
> tool — every Python repo ships a `[tool.towncrier]` config and a
> `changelog.d/` fragment directory. The language-agnostic release rules
> (auto-release workflow, version policy) live in the
> [repo baseline](repo-baseline.md#changelog-releases).

## What towncrier does

[towncrier](https://towncrier.readthedocs.io) aggregates per-PR newsfragments
into a single `CHANGELOG.md`. Instead of hand-editing `CHANGELOG.md` — which
creates merge conflicts and lost entries — each PR drops a one-line fragment
into `changelog.d/`. At release time, towncrier compiles them into the
changelog and removes the fragments.

This is the workflow used by pip, Twisted, PyPA build, and pulp. The fleet
already uses towncrier-style fragment directories; standardizing the config
makes the tooling predictable across repos.

## Configuration

Every Python repo MUST include the following block in `pyproject.toml`:

```toml
[tool.towncrier]
directory = "changelog.d"
filename = "CHANGELOG.md"
# package = "<python_package_name>"   -- uncomment for repos that ship a
#                                       Python package; pulls the version
#                                       from __version__. For docs-only or
#                                       non-Python repos, omit it — the
#                                       release workflow supplies --version.
start_string = "<!-- towncrier release notes start -->\n"
# .gitkeep keeps changelog.d/ present after a release consumes every
# fragment (git drops empty dirs; baseline-check requires the dir).
ignore = [".gitkeep"]

[[tool.towncrier.type]]
directory = "breaking"
name = "Breaking"
showcontent = true

[[tool.towncrier.type]]
directory = "feature"
name = "Added"
showcontent = true

[[tool.towncrier.type]]
directory = "bugfix"
name = "Fixed"
showcontent = true

[[tool.towncrier.type]]
directory = "misc"
name = "Changed"
showcontent = true

# Optional — add only if the repo uses these fragment types:
# [[tool.towncrier.type]]
# directory = "doc"
# name = "Documentation"
# showcontent = true
#
# [[tool.towncrier.type]]
# directory = "removal"
# name = "Removed"
# showcontent = true
```

### Field reference

- **`directory`** — always `"changelog.d"`. The fragment directory lives at
  the repo root, next to `CHANGELOG.md`.
- **`filename`** — always `"CHANGELOG.md"`. The compiled changelog file.
- **`package`** — the Python package name (e.g. `"robotsix_foo"`). Towncrier
  reads `__version__` from it to populate the release heading. Omit for
  repos that do not ship a Python package (docs-only repos, config repos);
  the release workflow passes `--version` explicitly.
- **`start_string`** — the marker towncrier inserts content after. The
  `<!-- towncrier release notes start -->` comment, followed by a newline,
  is the fleet standard. This keeps the header and any hand-written
  preamble above the marker untouched.
- **`ignore`** — always includes `".gitkeep"` so an empty `changelog.d/`
  survives `git` directory pruning between releases.
- **`[[tool.towncrier.type]]`** — one block per fragment suffix. The
  `directory` field is the fragment file extension (`.breaking`,
  `.feature`, `.bugfix`, `.misc` — towncrier strips the leading dot).
  The `name` field is the heading in the compiled changelog. All four
  canonical types are required; optional types (`doc`, `removal`) are
  added only when the repo uses them.

## Fragment format

Fragments are Markdown files in `changelog.d/` named with the convention:

```text
<timestamp>Z-<slug>-<short-hash>.<type>.md
```

The file body is a single line (or short paragraph) written in the past
tense, describing the change from the user's perspective:

```text
Fix the mail poller failing to reconnect after a DNS change.
```

- **One fragment per PR.** The PR author writes the fragment as part of
  the change — parallel PRs never conflict on `CHANGELOG.md`.
- **The `skip-changelog` PR label** exempts a PR from the fragment
  requirement. Use it for purely mechanical changes (CI tweaks, test-only
  fixes, tooling updates) where there is genuinely nothing to record.
- **Fragment filenames include a timestamp and hash** so they are
  universally unique — no naming collisions even across forks or
  rebases.

## CI enforcement

Every Python repo's CI MUST run `towncrier check` on pull requests:

```yaml
- name: Check changelog fragments
  run: towncrier check --compare-with origin/${{ github.event.pull_request.base.ref }}
```

If a PR has no fragment and no `skip-changelog` label, the check fails
with a message listing the expected fragment types.

For repos using pre-commit, the check can also run locally:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: towncrier-check
      name: towncrier check
      entry: towncrier check --compare-with origin/main
      language: python
      pass_filenames: false
      always_run: true
```

## Release step

The shared auto-release workflow runs `towncrier build` at release time:

```bash
towncrier build --yes --version "$NEXT_VERSION"
```

- `--yes` — non-interactive, suitable for CI.
- `--version` — the next version string (the release workflow derives this
  from the fragment types present: any `breaking` or `feature` → minor
  bump, else patch).
- Towncrier deletes the consumed fragments, appends the new section to
  `CHANGELOG.md`, and the release workflow commits both changes.

## Failure modes this prevents

- **Merge conflicts on `CHANGELOG.md`.** Without fragments, every PR that
  edits the changelog produces a conflict. Per-PR fragments eliminate this
  entirely.
- **Lost changelog entries.** Hand-editing a shared file under time
  pressure (release day) routinely drops entries. Towncrier compiles from
  fragments that were reviewed as part of each PR — nothing is lost.
- **Inconsistent changelog style.** Without a tool, each author writes
  changelog entries differently (some past tense, some imperative, some
  bullet lists, some prose). Towncrier + a fragment convention enforces
  one style.
- **Release workflow coupled to changelog format.** Without a standard
  marker (`start_string`), the release workflow cannot safely append to
  `CHANGELOG.md`. The marker gives the workflow a known insertion point.
