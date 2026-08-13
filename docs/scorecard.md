# OpenSSF Scorecard (not used)

> **Scope: fleet-wide.** robotsix repos **do not** run OpenSSF Scorecard.
> Do not add `.github/workflows/scorecard.yml` to a repo or to the
> repo-scaffold templates.

[OpenSSF Scorecard](https://securityscorecards.dev/) is a supply-chain
health audit that produces a single numeric score. The fleet evaluated it
and dropped it (operator decision, 2026-08-13). This page records the
decision and the replacement coverage, so a future proposal to re-add it
finds the answer instead of re-litigating it.

## The rule

robotsix repos **do not** run OpenSSF Scorecard. Do not add
`.github/workflows/scorecard.yml` to a repo or to the repo-scaffold
templates. Companion tickets remove the workflow from the three repos that
had it (robotsix-chat, robotsix-board, robotsix-calendar-agent).

## What replaces it

The supply-chain properties Scorecard would score are already gated
repo-locally, and harder:

- **zizmor** — workflow security (dangerous-workflow patterns, token
  permissions, template injection).
- **actionlint** — workflow syntax.
- **workflow-permissions audit** — least-privilege `permissions:` blocks.
- **Dependabot / `uv audit`** — dependency CVEs.
- **Trivy** — container CVEs.

These gates block a PR; Scorecard only scored it after the fact.

## Why it was dropped

1. **It was never a fleet standard — an accident of history.** Scorecard
   existed on 3 of 14 repos; coverage that partial gives no fleet-wide
   signal, just three repos carrying a workflow the other eleven do not.
2. **It duplicates gates the fleet already runs, more weakly.** Its
   meaningful checks — action pinning, token permissions, dangerous
   workflow patterns, branch protection — are already enforced repo-locally
   and harder by zizmor, actionlint, and the workflow-permissions audit.
   Those block a PR; Scorecard only scores it afterwards.
3. **`publish_results` has no consumer.** Publishing exists so third
   parties can read a score on deps.dev or a badge; nothing outside the
   fleet consumes these repos that way, so the published score is
   write-only data — while the publish step still depends on the external
   OpenSSF API and can redden a pipeline when that API is unavailable.
4. **It is compliance theatre.** The fleet's own stance is "no SLAs, no
   enterprise ceremony, no compliance theatre."

## Failure prevented

Drift between the three repos that carried Scorecard and the other eleven,
write-only published scores, and pipeline red on an external API the fleet
does not consume — while the actual supply-chain properties stay gated by
zizmor, actionlint, the permissions audit, Dependabot/`uv audit`, and Trivy.

## See also

- [Security posture](security-posture.md) — the per-gate controls that
  replace Scorecard.
- [GitHub Actions security](github-actions-security.md) — the zizmor
  workflow audit.
- [Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)
