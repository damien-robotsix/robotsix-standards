# Issue and PR templates

> **Scope: every robotsix repository.** Libraries, deployable components, and
> the standards repo itself all ship the same four onboarding files so every
> contributor — human or AI agent — starts from the same structured workflow.

## Why this exists

A repo with no issue or PR templates receives bug reports that lack environment
details, feature requests with no motivation, and pull requests that skip
pre-commit validation. Contributors waste cycles in follow-up questions instead
of reproducing or reviewing. New contributors — especially AI agents — have no
single place (outside AGENT.md) to find local-setup and commit-discipline
instructions.

Without structured templates the same failure modes repeat across the fleet:

- Bug reports arrive as one-line descriptions with no stack, version, or
  reproduction steps; the maintainer has to ask for every detail individually.
- PRs land without pre-commit passes, tests, or changelog fragments; CI catches
  some of this but the contributor never sees the checklist that would have
  prevented the round-trip.
- New contributors (human and AI alike) guess at local setup, PR workflow, and
  code rules because `CONTRIBUTING.md` is absent.

## The rule

**Every robotsix repository SHALL include these four files:**

| File | Purpose |
|---|---|
| `.github/ISSUE_TEMPLATE/bug_report.md` | Structured bug report with environment, reproduction steps, expected vs actual behaviour, and an "affects AI agent workflow?" flag. |
| `.github/ISSUE_TEMPLATE/feature_request.md` | Feature request with motivation, use case, proposed solution, and an "AGENT.md update needed?" flag. |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR checklist: pre-commit passes, tests added, changelog entry, AGENT.md updated if applicable, and an "affects AI agent workflow?" flag. |
| `CONTRIBUTING.md` | Local setup, lint/test instructions, PR workflow, and a pointer to `AGENT.md` as the canonical code-rules source. |

New repos created from the language template SHALL include these four files
from the start.

**Failure mode prevented:** contributors — human or AI — interact with the
repo through GitHub's default blank-text fields with no guidance about what
information is expected and what pre-submit checks must pass. The result is
incomplete reports, missed validation steps, and repeated round-trips that
burn maintainer attention and contributor goodwill.

### Template content

The canonical templates live in this repo's `.github/` directory. Repos copy
them and fill in any repo-specific details (e.g. language-specific setup
commands in `CONTRIBUTING.md`).

The templates include two robotsix-specific fields not found in generic
GitHub templates:

**"Affects AI agent workflow?"** — a binary flag on every bug report, feature
request, and pull request. It alerts the reviewer that the change may alter how
refine, implement, or review agents operate, so agent correctness must be
verified as part of the review. This flag exists because the fleet has
autonomous agent workflows that consume the same tooling and conventions as
human contributors.

**"AGENT.md update needed?"** — a flag on feature requests asking whether the
repo's `AGENT.md` (the accumulated working-knowledge file for both humans and
agents) must be updated to document the new behaviour. This prevents
`AGENT.md` from drifting out of date as features land.

### CONTRIBUTING.md structure

Every `CONTRIBUTING.md` must include:

| Section | Content |
|---|---|
| **Setup** | Clone command, install command (`uv sync`, `npm install`, etc.) — the 2–4 commands that produce a working dev environment. |
| **Lint and test** | The exact commands CI runs (`pre-commit run --all-files`, `pytest`, language-specific type-checkers). |
| **PR workflow** | Branch → pre-commit → push → PR → squash-merge flow. Mention the changelog-fragment requirement and the `skip-changelog` label. |
| **Code rules** | A single sentence pointing to `AGENT.md` as the canonical rules source — never restate rules here. |

**Failure mode prevented:** a `CONTRIBUTING.md` that restates code rules
creates a second copy that drifts from `AGENT.md`. The pointer pattern keeps
one canonical source — AGENT.md — and `CONTRIBUTING.md` as the setup-and-flow
companion.

### Relationship to AGENT.md

`AGENT.md` is the repo's accumulated working-knowledge file for **both** human
contributors and AI agents (see the [repo baseline](repo-baseline.md#agentmd)).
`CONTRIBUTING.md` is the onboarding companion — it tells you how to set up and
submit, but `AGENT.md` tells you what the codebase conventions are. The two
files are complementary: `CONTRIBUTING.md` links to `AGENT.md` for code rules,
and `AGENT.md` assumes the contributor already knows the setup from
`CONTRIBUTING.md`.

### Docs-nav surfacing

Repos that publish an MkDocs site must surface `CONTRIBUTING.md` in the docs
nav — see [Contributor guide in docs nav](contributing-in-nav.md).

## What NOT to do

- **Do not restate code rules in `CONTRIBUTING.md`.** Point to `AGENT.md`
  instead — one source of truth, no drift.
- **Do not remove the robotsix-specific fields** ("affects AI agent workflow?",
  "AGENT.md update needed?"). These flags exist because the fleet has
  autonomous agent workflows that other projects' templates do not account for.
- **Do not ship `CONTRIBUTING.md` without a Setup section.** A file that says
  only "see AGENT.md" is not a contributor guide — it is a redirect that
  frustrates first-time contributors who need concrete setup commands.
