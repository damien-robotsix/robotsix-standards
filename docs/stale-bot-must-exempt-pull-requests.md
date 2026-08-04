# Stale bot must exempt pull requests

> **Scope: every repository running `actions/stale`.** The stale action
> is for issue hygiene — never for auto-closing contributed pull requests.
> Every `stale.yml` workflow must disable pull-request staling and closing
> entirely by setting `days-before-pr-stale: -1` and
> `days-before-pr-close: -1`.

## The rule

**Every `stale.yml` workflow must exempt pull requests from both staling
and closing.** Per `actions/stale`'s documented semantics, setting a
`days-before-*` input to `-1` disables that operation for the corresponding
type entirely. The workflow must include:

```yaml
days-before-pr-stale: -1
days-before-pr-close: -1
```

This preserves automated issue-staleness triage while ensuring no
contributor's pull request is ever auto-closed by the stale bot.

## Why

A pull request is real contributed work. Auto-closing it after a period of
inactivity discards that effort and actively discourages contributors —
the contributor receives a message telling them their work will be closed,
and then the bot follows through.

The near-universal convention among mature open-source projects (FastAPI,
Docusaurus, pandas) and in the ROS 2 lineage that the source repo's own
stale workflow cites (Navigation2, MoveIt2) is: keep issue hygiene, but
never auto-close PRs.

The failure without this rule is visible in any repo that copies the
action's documented default `days-before-stale` / `days-before-close`
global pair without the PR-specific overrides: `actions/stale` applies
those values to pull requests as well, and contributed PRs begin
disappearing after two weeks of inactivity.
