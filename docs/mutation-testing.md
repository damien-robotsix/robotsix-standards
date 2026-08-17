# Mutation testing (mutmut)

> **Scope: every Python repository with ≥70% test coverage and a meaningful
> test suite.** Repos below the threshold — or whose tests exercise no real
> logic — are unaffected.

## Why this exists

Coverage percentage measures which lines *execute*, not whether any test
*checks what they do*. A test that calls a function and discards its result
counts as covered; a wrong return value ships at 100% coverage. Mutation
testing closes that gap by mutating the source — flipping `>` to `<`,
deleting statements, swapping `and`/`or` — and re-running the suite. Every
mutant that survives is a logic path no test asserts on.

The established pattern in the Python OSS ecosystem (FastAPI, Pydantic,
httpx, and similar projects) is an **advisory weekly cron**, never a
per-commit gate, for two reasons:

- **mutmut exits non-zero even when zero mutants survive.** There is no
  `--fail-under` threshold
  ([mutmut#49](https://github.com/boxed/mutmut/issues/49)), so a blocking CI
  step would be permanently red.
- **A full-repo run takes 30–90 minutes.** Running it on every push would
  dominate CI minutes for a signal that changes slowly.

The weekly cron pipes the run through `|| true`, saves the HTML report as a
workflow artifact, and writes the mutation score to the workflow summary —
the signal stays visible (a score trend across weeks) without ever blocking
a merge.

**Failure mode:** a repo with high coverage and no mutation testing can carry
untested logic for years — every unasserted branch, default argument, and
boundary condition is invisible to `coverage.py`. Green coverage plus no
mutation signal equals false confidence in the test suite.

## The rule

Every Python repository with ≥70% test coverage and a meaningful test suite
**should** run mutmut as a weekly advisory cron:

1. Declare the `[tool.mutmut]` config in `pyproject.toml` (below).
2. Add mutmut to the `dev` dependency group so `uv run mutmut` resolves in
   CI.
3. Ship `.github/workflows/mutation-test.yml` on a weekly `schedule`, plus
   `workflow_dispatch` for manual runs.
4. Pipe `uv run mutmut run` through `|| true` — the job must never fail on
   surviving mutants.
5. Upload the `html/` report as a workflow artifact and write the mutation
   score to `$GITHUB_STEP_SUMMARY`.

**Failure mode (blocking gate):** promoting mutmut to a required check makes
every run red, because mutmut has no threshold knob — there is no
configuration fix that turns the job green. The gate is either ignored as
"always red" or deleted outright, both strictly worse than an advisory run.
The cron must be non-blocking by construction.

## pyproject.toml config

```toml
[tool.mutmut]
source_paths = ["src/"]
pytest_add_cli_args_test_selection = ["tests/"]
```

- `source_paths = ["src/"]` scopes mutation to the package source, not tests
  or tooling.
- `pytest_add_cli_args_test_selection = ["tests/"]` selects the test
  directory when mutmut re-runs the suite per mutant.

The `backup = false` line that older mutmut examples show is a `setup.cfg`-era
key: mutmut 3.x does not read `backup` from `pyproject.toml`, so it is
omitted here — including it would be silently ignored dead config.

**Failure mode:** without `source_paths`, mutmut defaults to mutating the
current directory — including test files — which wastes CI minutes and
produces nonsense survivors. A mutated test suite that still passes says
nothing about the product code.

## Weekly cron workflow

The per-repo caller workflow is:

```yaml
name: Weekly mutation test
on:
  schedule:
    - cron: '0 6 * * 2'  # Tuesday 06:00 UTC (offset from Monday container scan)
  workflow_dispatch:
permissions:
  contents: read
jobs:
  mutate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v5
        with: { enable-cache: true, cache-python: true }
      - run: uv sync --locked --group dev
      - run: uv run mutmut run --no-progress || true
      - run: uv run mutmut report
      - run: uv run mutmut html
      - uses: actions/upload-artifact@v4
        with:
          name: mutmut-html-report
          path: html/
      - run: |
          SCORE=$(uv run mutmut results | tail -1 | grep -oP '\d+\.\d+' || echo "N/A")
          echo "### Mutation score: ${SCORE}%" >> $GITHUB_STEP_SUMMARY
```

- **`cron: '0 6 * * 2'`** — Tuesday 06:00 UTC, deliberately offset from the
  Monday container-scan cron so the two heavy jobs never compete for runner
  minutes.
- **`|| true`** — absorbs the non-zero exit mutmut reports when mutants
  survive; the job stays green and the report carries the signal.
- **The `html/` artifact** — `uv run mutmut html` writes the browsable
  survivor report to `html/`; uploading it makes every week's result
  inspectable without re-running the 30–90 minute job.
- **The step summary** — the mutation score lands in the run summary so the
  weekly trend is visible at a glance.

**Failure mode:** without `|| true`, the first week a mutant survives the job
goes red and, with no threshold to tune, the workflow gets muted or removed
— the signal is lost. Without the artifact and summary steps, a completed
run leaves nothing a human can read — 45 CI minutes spent on no output.

This workflow is a per-repo copy; there is no shared reusable workflow for
mutmut. If the fleet later promotes it to a reusable workflow in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows),
the caller template must move to that repo's README and version with the
workflow (see [Python CI workflow](python-ci-workflow.md)).
