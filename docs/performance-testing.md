# Performance baseline testing (pytest-benchmark)

> **Scope: deployable components that serve HTTP APIs.** The rule is a
> recommendation (`should`), not a mandate. Libraries with hot code paths *may*
> adopt the same pattern for those paths, but they are out of this rule's scope.
> Low-traffic services *may* defer adoption — see [Opt-out](#opt-out).

## Why this exists

Coverage and correctness gates tell you a change still *works*; they say nothing
about whether it got *slower*. A refactor that adds an N+1 query, drops an index
hint, or serialises a response the slow way ships green — the response-time
regression is invisible until it reaches production traffic. High-impact
endpoints (list aggregations, summary/rollup endpoints) are where this hurts
most and where nobody notices until a dashboard is already red.

A survey of the fleet (robotsix-cost-monitor: 24 test modules, 80% coverage
floor) confirmed there is no `pytest-benchmark` dependency, no performance
tests, and no CI performance step anywhere. Without a documented baseline
pattern each service either invents its own or, more commonly, ships nothing —
so regressions merge fleet-wide undetected.

[pytest-benchmark](https://pytest-benchmark.readthedocs.io/) closes that gap: it
times a function across many rounds, records the statistics, and can compare a
run against a saved baseline. Run in-process against a FastAPI `TestClient`, it
gives a repeatable per-endpoint latency number without standing up a server.

**Failure mode:** a service with high coverage and no performance baselines can
accumulate response-time regressions for months — every added query, extra
serialization pass, and unindexed filter is invisible to `coverage.py` and to
correctness tests. Green tests plus no timing signal equals false confidence
that performance is stable.

## The rule

Every deployable component serving an HTTP API **should** carry a
pytest-benchmark baseline for its high-impact endpoints and run it as an
**advisory, non-blocking** CI signal:

1. Declare `pytest-benchmark>=4.0` (or the current major) in the test/dev
   dependency group and lock it via `uv.lock` like every other dev dependency.
2. Put benchmark tests under `tests/` in a dedicated module
   (`tests/benchmarks/test_bench_<area>.py`), using the `benchmark` fixture
   against in-process endpoints (FastAPI `TestClient`).
3. Target the repo's high-impact endpoints — list aggregations and
   summary/rollup endpoints — not every route.
4. Exclude benchmarks from the normal (blocking) test run so they never inflate
   the test gate's runtime.
5. Run the benchmarks in a **scheduled or non-required** CI job that reports a
   comparison to the workflow summary and **never** as a required status check.

Timing-sensitive CI jobs still declare `timeout-minutes` per the
[repo baseline](repo-baseline.md).

## Dependency

Add pytest-benchmark to the same test/dev dependency group as pytest, and lock
it:

```toml
[dependency-groups]
dev = [
  # ...existing dev deps...
  "pytest-benchmark>=4.0",
]
```

- `pytest-benchmark>=4.0` — a lower bound on the current major; pin the upper
  bound only if a specific release breaks. It resolves through `uv sync
  --locked` in CI exactly like every other dev dependency.

**Failure mode:** an unlocked or missing benchmark dependency means the
scheduled job either fails to resolve or silently installs a floating version,
so the "baseline" it records is not reproducible against the previous run.

## Test pattern

Benchmark tests live under `tests/benchmarks/` and drive the app in-process
through a `TestClient`, so there is no network or server-startup variance in the
measured number:

```python
# tests/benchmarks/test_bench_summary.py
import pytest
from fastapi.testclient import TestClient

from myservice.app import app


@pytest.fixture(scope="module")
def client() -> TestClient:
    return TestClient(app)


@pytest.mark.benchmark
def test_summary_endpoint_latency(benchmark, client: TestClient) -> None:
    # Target a high-impact endpoint: a list aggregation / summary route.
    def call() -> None:
        response = client.get("/v1/summary?window=30d")
        assert response.status_code == 200

    benchmark(call)
```

- The `benchmark` fixture runs `call` across many rounds and records the
  statistics; the assertion inside keeps the benchmark honest (a route that
  500s is not a valid baseline).
- Scope the client fixture to the module so app construction is not part of the
  measured work.

Benchmark tests must be **excluded from the normal test run** so they never
inflate the blocking test gate's runtime. Either disable them by default in
`pyproject.toml` addopts and let the scheduled job re-enable them:

```toml
[tool.pytest.ini_options]
addopts = "--benchmark-disable"
markers = [
  "benchmark: performance baseline tests (advisory, run in the scheduled job only)",
]
```

`--benchmark-disable` still *collects and runs* the test bodies (so they count
toward correctness) but skips the timing loop, keeping the standard job fast.
Alternatively, mark the tests with `@pytest.mark.benchmark` and deselect them in
the standard CI test job with `-m "not benchmark"`. Either way the blocking
gate never runs the timing loop.

**Failure mode:** benchmarks left in the blocking test job run their full
multi-round timing loop on every push and PR, adding minutes to the gate every
developer waits on — CI runtime creep that pressures the team to weaken the
whole test suite.

## CI integration — advisory, non-blocking by construction

The benchmark run belongs in a **scheduled workflow** (weekly `schedule` plus
`workflow_dispatch` for manual runs) or a **non-required PR job** — mirroring
the [mutation-testing](mutation-testing.md) advisory-cron pattern. The job:

1. Runs `pytest --benchmark-only --benchmark-min-rounds=5
   --benchmark-json=bench.json` (the `benchmark` marker / `--benchmark-enable`
   re-enables the timing loop the standard config disables).
2. Uploads `bench.json` as a workflow artifact so every run's numbers are
   inspectable and downloadable.
3. Compares against the previous run's artifact with `--benchmark-compare` and
   `--benchmark-compare-fail=median:20%`, writing the comparison to the
   **workflow summary** (`$GITHUB_STEP_SUMMARY`) — for visibility, never as a
   required status check.

The job declares `timeout-minutes` per the [repo baseline](repo-baseline.md).
Per the standards convention, the caller workflow YAML is not embedded here:
like every other CI job it belongs in the per-repo `.github/workflows/` (or, if
the fleet later promotes it to a reusable workflow, in the
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
README, versioned with the workflow — the same rule
[mutation-testing](mutation-testing.md) states for its cron).

### Why not a blocking >5% gate

The draft that seeded this standard proposed a **blocking** CI step that fails
on any regression greater than 5%. This standard deliberately **deviates** from
that: performance comparison must **not** be a blocking gate.

Free-tier GitHub-hosted runners (see [free-tier only](free-tier-only.md)) are
shared VMs with noisy neighbours and high run-to-run timing variance — swings
well above 5% between two identical runs are routine. A 5% blocking threshold
therefore produces chronic false-red CI: the job fails on runner noise, not on
real regressions. That is exactly the "always red → gate gets silenced" failure
mode the [mutation-testing](mutation-testing.md) standard documents — a gate
nobody can keep green gets muted or deleted, and the signal is lost either way.

The standard is therefore **advisory reporting with a generous (≥20%)
comparison threshold**. A repo running on a **self-hosted runner with stable,
dedicated hardware** MAY tighten the threshold or promote the comparison to a
required check — but only with a justifying comment at the call site explaining
the hardware assumption, the same way a lint suppression carries its
justification.

**Failure mode:** a blocking timing gate on shared free-tier runners fails on
run-to-run noise rather than real regressions; with no threshold that stays
green on shared hardware, the job is muted or removed and the performance
signal disappears — strictly worse than an advisory run that stays visible.

## Opt-out

Low-traffic services may defer adopting performance baselines. Record the
deferral in the service's `AGENT.md` (a one-line note stating the service is
low-traffic and baselines are deferred) so the decision is explicit and
revisitable, rather than an undocumented gap.

## See also

- [Pytest practices](pytest.md) — strictness config the benchmark module also
  inherits (`--strict-markers` requires the `benchmark` marker be registered).
- [Mutation testing (mutmut)](mutation-testing.md) — the advisory,
  non-blocking-cron pattern this page mirrors.
- [Python CI workflow](python-ci-workflow.md) — the blocking `ci.yml` shape the
  benchmark job stays out of.
- [FastAPI test isolation](fastapi-test-isolation.md) — the `TestClient` /
  dependency-override pattern benchmark tests build on.
