# Python `__main__.py` exit-code forwarding

> **Scope: every Python repository that ships a CLI via `console_scripts`
> entry points AND a `__main__.py` shim.** The rule applies to every fleet
> package whose `pyproject.toml` declares `[project.scripts]` entry points
> and whose source tree includes `src/<pkg>/__main__.py`.

A Python package that ships both console-script entry points and a
`__main__.py` shim for `python -m <pkg>` invocation MUST forward `main()`'s
return value to `sys.exit()` — so that `python -m <pkg>` yields the **exact
same process exit code** as the installed console script.

## The standard

**`__main__.py` MUST end with `sys.exit(main())`** where `main` returns an
`int` or `enum.IntEnum` exit status. `__main__.py` MUST NOT call `main()`
bare — falling off the end always yields status 0, silently discarding the
returned exit code.

**`main()` itself SHOULD NOT call `sys.exit`.** Let callers decide: the
console-script entry point's wrapper (setuptools) already wraps the return
with `sys.exit()`, and `__main__.py` forwards it explicitly. A `main()` that
internally calls `sys.exit()` takes control away from every possible caller —
including tests that want to inspect the return value.

### The correct pattern

```python
# src/<pkg>/__main__.py
import sys
from <pkg>.cli import main

sys.exit(main())
```

### The incorrect pattern

```python
# src/<pkg>/__main__.py — WRONG: exit code lost
from <pkg>.cli import main

main()  # returns int, but process always exits 0
```

### The `main()` function

`main()` should return an `int` (or `enum.IntEnum` for named constants) and
never call `sys.exit` internally:

```python
# src/<pkg>/cli/__init__.py
from enum import IntEnum

class ExitCode(IntEnum):
    OK = 0
    ERRORS = 1
    FATAL = 2

def main(argv: list[str] | None = None) -> ExitCode:
    ...
    return ExitCode.ERRORS  # caller forwards to sys.exit
```

A guard block for direct-file execution is harmless but irrelevant — the
`-m` path goes through `__main__.py`, not through `__name__ == "__main__"`:

```python
if __name__ == "__main__":  # fires on `python cli/__init__.py`, not `-m`
    sys.exit(main())
```

## Why setuptools doesn't save you

Setuptools wraps console-script entry points in its own `sys.exit()` call,
so the installed `robotsix-<name>` binary reports the correct exit code
automatically. But `python -m <pkg>` goes through `__main__.py`, not the
entry-point machinery — setuptools never touches that path. `__main__.py`
must forward the return value itself.

## Failure modes this prevents

- **Silent success on failure.** `python -m <pkg>` called in a script or CI
  pipeline always exits 0 even when the command fails. The calling script
  proceeds as if everything succeeded — a `make lint` that runs
  `python -m robotsix_modules check` never sees a validation failure.
- **Divergent behaviour between invocation paths.** `robotsix-<name>` in a
  `docker compose` healthcheck reports correct exit codes, but
  `python -m <pkg>` in a developer script or CI step does not — the two
  invocation paths behave differently with no warning.
- **Undetectable CI breakage.** A CI step that runs `python -m <pkg> lint`
  will never fail, even when the linter finds violations, because the
  process always exits 0.

## Canonical reference

- Python stdlib docs (`__main__.py`): the module-entry point must explicitly
  forward `main()`'s return to `sys.exit()`; falling off the end always yields
  status 0, discarding any returned `int`.
- pip ships exactly this pattern in `src/pip/_internal/__main__.py`:

  ```python
  import sys
  from pip._internal.cli.main import main as _main

  if __name__ == "__main__":
      sys.exit(_main())
  ```
