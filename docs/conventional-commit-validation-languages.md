# Conventional commit validation (multi-language)

> **Scope: non-Python repositories** (Node.js, PHP, ROS 2, Dart, and any other
> language in the fleet). This page is the multi-language companion to
> [Conventional commit validation](conventional-commit-validation.md), which
> prescribes the **Python** toolchain (commitizen in `pyproject.toml`). The
> commit-message grammar and prefix-to-bump mapping are canonical in
> [release-please § Conventional commits](release-please.md#conventional-commits);
> this page only covers *how each ecosystem wires the local `commit-msg` hook* —
> it never restates the grammar or the two canonical rules.

Every repo that wires release-please must validate commit messages per
[release-please rule 1](release-please.md#1-every-repo-wires-release-please),
regardless of implementation language. That requirement is **two layers** — a
local `commit-msg` pre-commit hook for fast feedback, and a commitlint CI check
on the PR title as the authoritative gate — exactly as the
[Python page explains](conventional-commit-validation.md#why-both-layers).
Neither layer substitutes for the other.

## What is the same across every language

**The CI layer is language-agnostic.** The commitlint CI check validates the
**PR title** — the subject of the squash-merge commit the fleet default produces
— which is a plain string with no relationship to the repo's language. Every
repo, Python or not, wires the *same* shared caller stub from the
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
README. Following the fleet convention that standards pages never embed
GitHub-workflow YAML, this page does not reproduce it; the stub is version-pinned
alongside the workflow it calls so the two cannot drift.

**Only the local `commit-msg` hook differs by language**, because that hook runs
through whatever toolchain the repo already carries. The fleet runs the
[`pre-commit`](https://pre-commit.com) framework in every repo
(see [Pre-commit baseline](pre-commit-baseline.md)), so the local hook is wired
in `.pre-commit-config.yaml` on the `commit-msg` stage in every language below —
and, as in Python, `pre-commit install --hook-type commit-msg` is required
because the default `pre-commit install` registers only the `pre-commit` stage.

## Language-agnostic hook (PHP, ROS 2, Dart, and others)

For any repository whose language has **no first-class Conventional Commits
linter** — PHP, Dart, and ROS 2 packages that are not pure Python among them —
use the language-agnostic
[`conventional-pre-commit`](https://github.com/compilerla/conventional-pre-commit)
hook. It validates the message with no per-language runtime, so a PHP, Dart, or
C++/CMake repo does not have to add a Python or Node toolchain purely to lint
commit messages:

```yaml
  - repo: https://github.com/compilerla/conventional-pre-commit
    rev: v4.4.0
    hooks:
      - id: conventional-pre-commit
        stages: [commit-msg]
```

The `rev` follows the fleet pinning rule — a tagged release, bumped
deliberately, never a floating `main`/`master`. The hook's default ruleset
accepts the same prefix set release-please recognises, so no extra configuration
is required to match [release-please § Conventional commits](release-please.md#conventional-commits).

### PHP projects

PHP has no widely-adopted native Conventional Commits linter, and the fleet does
not add one: a PHP repo wires the language-agnostic `conventional-pre-commit`
hook above for the local layer and the shared commitlint caller stub for CI. Do
not pull a Node `@commitlint/cli` toolchain into a PHP repo solely to lint
commits — that adds a second language runtime the repo otherwise does not need.

### ROS 2 projects

A ROS 2 package that is pure Python follows the
[Python page](conventional-commit-validation.md) and uses commitizen in
`pyproject.toml`. A ROS 2 package built with `ament_cmake` / C++ (no
`pyproject.toml` to host `[tool.commitizen]`) uses the language-agnostic
`conventional-pre-commit` hook above, so the commit-msg layer does not depend on
a Python packaging file the package does not otherwise carry.

### Dart projects

Dart/Flutter has no first-class Conventional Commits linter in the fleet
toolchain, so a Dart repo uses the language-agnostic `conventional-pre-commit`
hook for the local layer and the shared commitlint caller stub for CI.

## Node.js projects

Node.js is the one non-Python ecosystem with a first-class toolchain, so a
Node repo uses it rather than the language-agnostic hook:

- **[commitlint](https://commitlint.js.org) validates.** Add
  `@commitlint/cli` and `@commitlint/config-conventional` as `devDependencies`
  and configure the conventional ruleset in `commitlint.config.js`
  (`module.exports = { extends: ['@commitlint/config-conventional'] };`). This
  is the same engine the CI check runs, so local and CI validation share one
  ruleset.
- **[cz-cli](https://github.com/commitizen/cz-cli) (`commitizen`) assists
  authoring.** It is the JavaScript equivalent of Python's commitizen: `git cz`
  prompts for a conforming type, scope, and subject. It is an authoring aid, not
  a gate — validation is still commitlint's job.

Wire the local `commit-msg` validation through the repo's existing `pre-commit`
framework with a `local` hook that calls the installed commitlint binary, so a
Node repo keeps one hook manager rather than adding a second
(`husky`) alongside `pre-commit`:

```yaml
  - repo: local
    hooks:
      - id: commitlint
        name: commitlint
        entry: npx --no-install commitlint --edit
        language: system
        stages: [commit-msg]
```

`--no-install` makes the hook fail loudly if `@commitlint/cli` is missing from
`devDependencies` rather than silently fetching an unpinned copy at commit time;
the version is pinned in `package.json` / the lockfile like any other
dependency.

## Rules

### 1. Non-Python repos validate commits with a language-appropriate local hook

**Rule:** Every non-Python repo that wires release-please carries a local
`commit-msg` pre-commit hook — `conventional-pre-commit` for languages with no
native linter (PHP, Dart, non-Python ROS 2), or a commitlint `local` hook for
Node.js — plus the shared commitlint CI check. The hook is registered on the
`commit-msg` stage and the repo's dev setup runs
`pre-commit install --hook-type commit-msg`.

**Rationale:** The local layer gives fast authorship feedback the CI gate cannot;
picking the hook that rides the toolchain the repo already carries avoids adding
a second language runtime (a Node toolchain in a PHP repo, a Python packaging
file in a C++ ROS 2 package) purely to lint commit messages.

> **Failure mode this prevents.** A non-Python repo, lacking the Python
> commitizen hook the baseline describes, ships with no local commit-msg
> validation at all. A malformed subject (`Fixed login`, `feature: add retry`,
> `WIP`) is authored with no feedback and, if the PR title repeats it, lands on
> the default branch; release-please does not recognise the prefix and silently
> drops the commit from the release PR — no version bump, no changelog entry,
> invisible until a consumer asks why a shipped fix is absent from the changelog.

### 2. The CI check is the same across languages; the hook never replaces it

**Rule:** Every repo — whatever its language — wires the one shared commitlint
CI caller stub from robotsix-github-workflows as a required status check on the
default branch. A repo must never substitute its local-language hook for the CI
check.

**Rationale:** The fleet squash-merges, so the subject release-please reads is
the PR title — a language-independent string no local `commit-msg` hook of any
language ever sees. The CI check validating that title is therefore identical
for a Python, Node, PHP, ROS 2, or Dart repo, and is the only layer that can
catch a malformed PR title.

> **Failure mode this prevents.** A Node (or PHP, Dart, ROS 2) repo installs its
> local commitlint/`conventional-pre-commit` hook, assumes commit messages are
> covered, and omits the CI caller stub. A contributor opens a PR with a
> free-text title (`Update the poller`); the squash-merge lands that
> non-conforming subject on the default branch, defeating the local layer
> entirely and breaking the release-please bump exactly as in rule 1.
