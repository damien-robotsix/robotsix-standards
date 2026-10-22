# Code coverage

> **Scope: every repository with a test suite.** This page is the
> cross-language rule for *what* coverage is measured, *which* reports are
> produced and *what* targets apply per area. The per-language configuration
> lives on the language pages: [Python](python.md#tests),
> [JavaScript](javascript.md#tests), [PHP](php.md).

## Why this exists

Coverage only helps when every repo measures it the same way. If repos use
different tools, report formats and thresholds, a percentage from one repo
can't be compared with a percentage from another. A repo that never publishes
a report gives reviewers nothing to check. And a single aggregate number can
hide untested core logic behind well-covered boilerplate.

## Failure modes this prevents

- **Invisible regressions.** Without a gated floor, coverage drifts down one
  PR at a time and nobody notices until a bug ships through an untested path.
- **Averaging away the core.** A repo at 82% overall can still have its
  validators or state machine at 50%. The aggregate passes the gate, but the
  code most likely to cause damage is the code least tested.
- **Unreadable reports.** If CI prints no per-file summary, reviewers can't
  see what a PR left untested. If CI keeps no machine-readable artifact,
  trend tools (Codecov, Coveralls, SonarQube) have nothing to ingest.
- **Gaming the number.** If the floor can be lowered per repo, it gets
  lowered to make a red PR green. The floor then measures nothing.

## The floor (gated)

**One fleet-wide floor: 80% overall, the same in every language.** This sits
inside the 75–85% band the wider ecosystem recommends for mature projects.
The floor is codified once in [Python practices → Tests](python.md#tests)
(how it is enforced, how it moves fleet-wide only, why there is no per-repo
threshold). [JavaScript](javascript.md#tests) applies the same number.
Don't restate or fork it here or in a repo.

## Per-area targets (advisory)

The floor is the only gated number. Within a repo, aim for these targets by
area. Reviewers use them when judging whether a PR's tests are adequate:

| Area | Target | Why |
|---|---|---|
| Core logic / critical paths (state machines, schedulers, money, auth) | **≥ 90%** | Bugs here corrupt data or break security. |
| Validators and business rules (config models, parsers, policy checks) | **≥ 90%** | Pure, cheap to test, and every branch is a user-visible rule. |
| Handlers / controllers / CLI glue | **70–80%** | Thin wiring around tested logic; integration tests cover the rest. |
| Whole project | **≥ 80%** (the gated floor) | See [the floor](#the-floor-gated). |

**Failure mode:** gating per-area targets would need a per-repo map of which
paths count as "core". That map drifts as modules move, and the gate goes
quietly wrong. Keep these targets advisory and enforce them in review. Pair
them with [mutation testing](mutation-testing.md) for core logic, because
line coverage alone can't show whether the tests *assert* anything.

## Measurement rules

1. **Measure product code only.** Scope coverage to the package source and
   exclude tests, vendored code and virtualenvs. If test files count toward
   the total, the percentage goes up without any product code being tested.
2. **Measure branches, not just lines,** wherever the tool supports it. A
   line with an untaken `else` otherwise reports as fully covered.
3. **Produce three outputs:**
   - **CI log: a text summary** per file or directory with missing lines, so
     reviewers can read the gap straight from the job log.
   - **CI artifact: one machine-readable XML report**, uploaded as a workflow
     artifact. Use the format the language's tool emits natively and that
     Codecov, Coveralls and SonarQube all ingest: **Cobertura XML** for
     Python (`coverage.xml`) and JavaScript, **Clover XML** for PHP.
     Don't add a conversion step just to make every repo emit the same XML
     dialect, because a converter is one more tool that can drift.
   - **Local: an HTML report** for interactive browsing. Don't commit it
     (it is gitignored build output, like `htmlcov/`).
4. **Uploading to an external service is opt-in.** The fleet default is the
   terminal summary plus the workflow artifact. Codecov and similar services
   are optional per repo and must stay non-blocking. See
   [free-tier only](free-tier-only.md).

## Per-language implementation

- **Python:** pytest-cov / coverage.py, with the standard `[tool.coverage]`
  block and the gated floor, as defined in
  [Python practices → Tests](python.md#tests) and run by the
  [Python CI workflow](python-ci-workflow.md). HTML locally through the
  `coverage-view` target of the [Makefile convention](python-makefile-convention.md).
- **JavaScript / TypeScript:** vitest with `@vitest/coverage-v8`
  (`vitest run --coverage`) and the floor in `thresholds`. See
  [JavaScript practices → Tests](javascript.md#tests). Configure the
  `text`, `html` and `cobertura` reporters.
- **PHP:** PHPUnit with a `<coverage>` / `<source>` block in `phpunit.xml`,
  run in CI with `--coverage-clover clover.xml --coverage-text`, and locally
  with `--coverage-html`.
  - **Driver:** in CI, use **PCOV**. It is line-coverage only and several
    times faster than Xdebug. Install it through `shivammathur/setup-php`
    with `coverage: pcov`. Locally, use PCOV for quick runs or Xdebug 3
    (`XDEBUG_MODE=coverage`) when you also need step debugging or branch
    coverage.
  - **Picking the driver:** PHPUnit has no flag that picks the driver. It
    uses whichever coverage extension is loaded. To force PCOV, load only
    PCOV, or set `XDEBUG_MODE=off` alongside it.
  - **Failure mode:** with no coverage extension loaded, PHPUnit warns
    "No code coverage driver available" and writes no report. Set
    `failOnWarning="true"` in `phpunit.xml` so this fails the job instead of
    shipping an empty artifact.
- **Other languages (Go, Dart, ROS 2 C++):** use the toolchain's native
  coverage (`go test -coverprofile=coverage.out ./...`,
  `flutter test --coverage`, `colcon test` with the coverage mixins). Apply
  the same three outputs and the same floor.
