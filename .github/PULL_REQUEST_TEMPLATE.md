# Pull request

## Pre-submit checklist

<!-- Check every box before marking the PR ready for review. -->

- [ ] Pre-commit hooks pass (`pre-commit run --all-files`)
- [ ] Tests added or updated for the change (unit + integration as appropriate)
- [ ] Changelog fragment added (or `skip-changelog` label applied if the change is purely mechanical)
- [ ] CI is green (lint, type-check, test, security gates)
- [ ] AGENT.md updated if the change affects agent workflows or repo conventions

## Affects AI agent workflow?

<!-- If this PR changes code that refine / implement / review agents interact
     with, describe the impact so the reviewer can verify agent correctness. -->

- [ ] Yes — explain below
- [ ] No

## Summary

<!-- One paragraph describing what this PR does and why. -->