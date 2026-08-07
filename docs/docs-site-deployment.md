# Docs site deployment

> **Scope: every repository that publishes its MkDocs site to GitHub Pages.**
> Repos with no published site are exempt. This is the *deployment* half of the
> docs story — [MkDocs build integrity](mkdocs-build.md) covers the *build*
> half, and a repo that publishes needs both.

## Why this exists

The shared `python-docs.yml` workflow deploys through the **Pages Actions**
(`actions/upload-pages-artifact` + `actions/deploy-pages`), not through
`mkdocs gh-deploy`. That choice has three consequences a calling repo must
honour, and none of them were written down.

The result, audited on 2026-08-07 across nine repos that publish docs: **six
different pins of the same shared workflow, four different caller-permission
shapes, three different Pages configurations, and three repos whose Docs
workflow had never once run.**

What makes this worth a standard rather than a bug fix is the failure mode. A
caller that requests permissions the shared workflow cannot satisfy fails at
**startup**: no logs, no checks, no annotation on the PR, no red anywhere. The
workflow simply never runs. Nothing in the fleet surfaces it, so it persists
indefinitely — auto-mail's had been dead for weeks before anyone noticed, and it
was noticed only by counting `startup_failure` entries in the run list.

## Rules

### 1. The caller grants exactly `contents: read`, `pages: write`, `id-token: write`

**Rule:** A repo calling `python-docs.yml` must set, on the calling **job**:

```yaml
jobs:
  deploy:
    permissions:
      contents: read    # the spine's build job checks out the repo
      pages: write      # the spine's deploy job publishes the artifact
      id-token: write   # OIDC auth for actions/deploy-pages
    uses: damien-robotsix/robotsix-github-workflows/.github/workflows/python-docs.yml@<sha>
```

**Rationale:** A caller job's `permissions` map **replaces** the token scopes
available to the called workflow — it does not merge with the workflow-level
default. Every scope not listed is zeroed. A called workflow whose jobs request
a scope the caller did not grant is rejected before execution.

All three are required together. Omitting any one is as fatal as granting none.

> **Failure mode.** Two real variants, both silent:
>
> - Granting `contents: write` (the `gh-deploy` shape) leaves all three unmet.
>   Observed on auto-mail and cost-monitor.
> - Granting `pages: write` + `id-token: write` but omitting `contents: read`
>   starves the build job's checkout. Observed on board — a repo pinning the
>   *same* shared revision as a working one, which is why "copy a repo that
>   works" is not a reliable substitute for the rule.

### 2. Repository Pages source must be "GitHub Actions"

**Rule:** The repo's Pages configuration must be build type `workflow`
(Settings → Pages → Source: *GitHub Actions*), not the legacy branch model.
Verify with:

```bash
gh api repos/<owner>/<repo>/pages --jq '.build_type'   # must print: workflow
```

**Rationale:** `actions/deploy-pages` publishes an artifact to the Pages
service. A repo still set to serve a `gh-pages` branch has nowhere to receive
it, so the workflow starts, builds, and fails at the final step.

**This rule and rule 1 must land together.** Fixing permissions alone converts
an invisible startup failure into a visible deploy failure — an improvement, but
not a working site.

> **Failure mode.** A repo bumps its `python-docs.yml` pin to a revision that
> switched from `gh-deploy` to the Pages Actions, and keeps its old permissions
> and Pages settings. Both halves of the contract silently break at once. This
> is exactly what happened to auto-mail.

### 3. The caller owns concurrency, and the group is `pages`

**Rule:** The calling workflow sets its own concurrency:

```yaml
concurrency:
  group: pages
  cancel-in-progress: false
```

**Rationale:** The shared spine deliberately sets **no** workflow-level
concurrency. Inside a called workflow, `${{ github.workflow }}` resolves to the
**caller's** workflow name, so a group built from it in the spine would deadlock
against a caller using the same expression. Concurrency therefore belongs to the
caller, and `pages` names the resource actually being serialised — the single
Pages deployment — rather than the workflow that happens to drive it.

Prefer `cancel-in-progress: false` for deployments: cancelling a half-finished
Pages publish is worse than queueing behind it.

### 4. Pin the shared workflow, and move pins deliberately

**Rule:** Call `python-docs.yml` at a full commit SHA with a trailing `# main`
comment, per [CI lint pinning](ci-lint-pinning.md). When bumping that pin,
re-read rules 1 and 2 — the pin is the mechanism by which a repo silently
changes deployment model.

**Rationale:** The permissions contract is a property of the *pinned revision*,
not of the workflow name. A repo on an older pin using `mkdocs gh-deploy` is
internally consistent with `contents: write` and legacy Pages, and works
correctly — robotsix-mill is in exactly that state and is not broken. It becomes
broken the moment its pin moves without its permissions and Pages settings
moving too.

> **Failure mode.** Six pins of one shared workflow across nine repos means six
> different contracts in force simultaneously. A fix verified against one repo
> tells you nothing about the next.

## Verifying a repo

Two commands answer both halves:

```bash
# rule 1: the caller's job-level grants
gh api repos/<owner>/<repo>/contents/.github/workflows/docs.yml \
  --jq '.content' | base64 -d | sed -n '/^jobs:/,$p'

# rule 2: the Pages build type
gh api repos/<owner>/<repo>/pages --jq '.build_type'
```

And the signal that something is wrong at all — because a startup failure
produces nothing else:

```bash
gh run list --repo <owner>/<repo> --workflow Docs --limit 10 \
  --json conclusion --jq '[.[].conclusion] | join(",")'
```

`startup_failure` in that output always means a permissions mismatch. There is
no other way for a run to die before producing a single log line.

## Exemptions

A repo may hand-roll its docs job instead of calling the shared spine (chat and
standards both do). Rules 2 and 3 still apply — they are properties of GitHub
Pages, not of the shared workflow. Rule 1 does not, since there is no called
workflow whose permissions to satisfy; the job's own `permissions` block simply
needs whatever its steps use.
