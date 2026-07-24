# Pytest strictness configuration

> **Scope: every Python repository.** These settings apply fleet-wide so
> every test suite fails loudly on deprecation warnings, unregistered markers,
> and unexpectedly-passing xfails.

## Why this exists

Without strictness settings, pytest silently ignores several classes of
problem that matter in CI:

- **Deprecation warnings from dependencies scroll past invisibly** — the
  first a team learns of a removed API is the upgrade that breaks at runtime.
- **Typos in `@pytest.mark.xxx` decorators are silently tolerated** — the
  marker is registered as an ad-hoc string, the test runs without it, and the
  intended filtering or skipping never happens.
- **`@pytest.mark.xfail` tests that start passing** (because the bug was
  fixed) continue to report as "expected failure" — the test suite never
  signals that the fix landed, so the xfail marker rots indefinitely.

Four mature ASGI/data projects — FastAPI, Starlette, Pydantic, and httpx —
all ship `filterwarnings = ["error"]` in their `pyproject.toml`. FastAPI and
Starlette additionally enable `--strict-markers` and `--strict-config`.
Codifying the convention here means every fleet repo inherits the same
discipline rather than each re-deriving it.

## Baseline settings (mandatory)

Every Python repository **must** include these two settings in
`[tool.pytest.ini_options]`:

```toml
[tool.pytest.ini_options]
filterwarnings = ["error"]
xfail_strict = true
```

- **`filterwarnings = ["error"]`** — turn every warning into an exception.
  This is the universal baseline across all four surveyed projects.
- **`xfail_strict = true`** — an `@pytest.mark.xfail` test that unexpectedly
  passes is reported as a failure (`XPASS(strict)`), flagging the stale
  marker so it can be removed.

**Failure mode:** without `filterwarnings = ["error"]`, dependency
deprecation warnings are invisible in CI output — the upgrade that removes
the deprecated API lands as a surprise breakage. Without `xfail_strict`,
fixed bugs stay marked as expected failures forever, and the test suite
never signals that the fix is real.

## Targeted warning ignores

Repos **may** add narrowly-scoped `ignore:` entries for third-party
`DeprecationWarning`s that are out of their control:

```toml
filterwarnings = [
    "error",
    "ignore::DeprecationWarning:third_party_package.*:",
    "ignore::DeprecationWarning:another_package.module:",
]
```

Each `ignore:` entry **must** include a `message` and/or `module` qualifier
so it silences only the specific warning it targets — never a bare
`"ignore::DeprecationWarning"`. Starlette, Pydantic, and httpx all follow
this pattern.

**Failure mode:** a bare `ignore::DeprecationWarning` suppresses every
deprecation in the entire test suite, including the project's own — the
setting becomes self-defeating.

## Recommended tier: strict markers and config

Repos **should** additionally enable marker and config strictness:

```toml
addopts = ["--strict-markers", "--strict-config"]
```

- **`--strict-markers`** — any `@pytest.mark.xxx` decorator whose marker
  name is not registered (via `markers` in `pyproject.toml` or a
  `pytest_configure` hook) raises an error instead of silently adding an
  ad-hoc marker.
- **`--strict-config`** — any unrecognised `[tool.pytest.ini_options]` key
  raises an error, catching typos in config.

FastAPI and Starlette both ship these settings.

**Failure mode:** without `--strict-markers`, a typo like
`@pytest.mark.smoke` (intended `smoke`) becomes a silently-registered ad-hoc
marker that no `-m` filter ever selects — the test is never run in the
targeted suite, and the mistake is invisible until a human notices the test
is missing from CI results.

## Full example

```toml
[tool.pytest.ini_options]
addopts = ["--strict-markers", "--strict-config"]
xfail_strict = true
filterwarnings = [
    "error",
    # Third-party deprecation warnings that the project cannot fix:
    # "ignore::DeprecationWarning:some_library.*:",
]
```
