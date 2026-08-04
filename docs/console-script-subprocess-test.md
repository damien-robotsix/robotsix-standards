# Console-script subprocess tests

> **Scope: every Python repository that ships `[project.scripts]` entry
> points in `pyproject.toml`.** The rule applies to every fleet package
> whose packaging declares console-script entry points (e.g.
> `robotsix-modules = "robotsix_modules.cli:main"`).

Every deployed CLI entry point must be tested as a **subprocess through the
installed console script** — not only through an in-process `main()` call and
not only through `python -m <pkg>`. The installed console script is the
primary user-facing interface (the documented `robotsix-<name>` binary), and
only a subprocess round-trip can verify the real `[project.scripts]` wiring.

## The standard

For each `[project.scripts]` key defined in `pyproject.toml`, the test suite
must include, at minimum:

1. **A subprocess test invoking the installed console script on valid input**
   asserting exit code 0.
2. **A subprocess test on missing or invalid input** asserting a nonzero exit
   code and the expected stderr marker.
3. **A graceful skip** (`pytest.skip`) when the script is not resolvable on
   `PATH` (e.g. via `shutil.which`), so the suite still runs in bare-dev
   environments that haven't installed the project's console scripts.

These tests **complement** (do not replace) existing in-process `main()` unit
tests and `python -m <pkg>` shim tests.

### The correct pattern

```python
import shutil
import subprocess

import pytest


def _script_path() -> str | None:
    """Return the installed console-script path, or None if not installed."""
    return shutil.which("robotsix-<name>")


@pytest.mark.skipif(_script_path() is None, reason="console script not installed")
def test_console_script_help():
    """The installed console script exits 0 on --help."""
    result = subprocess.run(
        [_script_path(), "--help"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "usage:" in result.stdout.lower() or "usage:" in result.stderr.lower()


@pytest.mark.skipif(_script_path() is None, reason="console script not installed")
def test_console_script_invalid_flag():
    """The installed console script exits nonzero on an unknown flag."""
    result = subprocess.run(
        [_script_path(), "--no-such-flag"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert "--no-such-flag" in result.stderr or "unrecognized" in result.stderr.lower()
```

### Using the console_scripts test fixture (pytest-console-scripts)

Repos may alternatively use the
[`pytest-console-scripts`](https://pypi.org/project/pytest-console-scripts/)
plugin, which provides a `console_script` fixture that runs installed entry
points as subprocesses:

```python
import pytest


pytest.importorskip("pytest_console_scripts")


def test_entrypoint_help(console_script):
    result = console_script("robotsix-<name>", "--help")
    assert result.returncode == 0


def test_entrypoint_invalid(console_script):
    result = console_script("robotsix-<name>", "--no-such-flag")
    assert result.returncode != 0
```

Add `pytest-console-scripts` as a test dependency (e.g. `[dependency-groups]
test` in `pyproject.toml`).

## Why in-process tests aren't enough

- **Console-script shim generation.** The packaging backend (uv/hatchling)
  generates a wrapper script that calls the entry-point function and wraps its
  return value with `sys.exit()`. An in-process `main()` call cannot observe
  this shim — argv parsing, stdout/stderr plumbing, and the actual process
  exit code seen by a shell are all invisible.
- **`[project.scripts]` wiring regressions.** A rename of the callable or a
  packaging-config change (e.g. switching from hatchling to a different
  backend) can silently break the installed binary. In-process tests and
  `python -m` tests don't exercise the entry-point mapping at all.
- **`python -m` only verifies the module path.** `python -m <pkg>` tests the
  `__main__.py` shim (see
  [`__main__.py` exit-code forwarding](python-main-py-forward.md)), but never
  touches the installed console-script wrapper — it's a different code path.

## Failure modes this prevents

- **Broken console script after refactor.** A rename of `cli:main` to
  `cli:entrypoint` in `pyproject.toml` while the callable is renamed in the
  source breaks the installed binary — but in-process tests and `python -m`
  tests all pass because they don't use the entry-point mapping.
- **Silent packaging regression.** A `pyproject.toml` change that drops or
  renames a `[project.scripts]` key goes undetected — CI smoke-tests the wheel
  install but no test actually runs the binary.
- **Shell-facing exit-code drift.** The `__main__.py` shim forwards the exit
  code correctly (verified by `python -m` tests), but the console-script
  wrapper has a different code path — a packaging-backend upgrade could change
  its behaviour without any test noticing.

## CI integration

Console-script subprocess tests run naturally as part of the normal test suite
when the package is installed (e.g. `pip install .` or `uv run pytest` with
the package in editable mode). When the script is not on `PATH`, the
`@pytest.mark.skipif` guard skips the subprocess tests gracefully, so the
suite still passes in environments that haven't installed the console scripts
(e.g. a bare `python -m pytest` in a checkout without `pip install -e .`).

The existing `wheel-install` CI job (which installs the built wheel and
smoke-tests it) already provides a suitable environment for these tests to
run without the skip guard — the script is on `PATH` after wheel install.

## Cross-reference

- **[Python `__main__.py` exit-code forwarding](python-main-py-forward.md)** —
  the `__main__.py` shim must forward `main()`'s return to `sys.exit()` so
  `python -m <pkg>` reports the same exit code as the installed console script.
- **[Pytest practices](pytest.md)** — `filterwarnings = ["error"]`,
  `xfail_strict = true`, and `--strict-markers` for every fleet test suite.
