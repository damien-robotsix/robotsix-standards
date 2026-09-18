# CLI documentation validation

> **Scope: every Python repository that ships a CLI and documents its command
> invocations** — README quick-starts, usage and how-to pages, `--help` text.
> A documented command line is part of the public interface: it must be
> exactly what the real parser accepts, and that contract must be enforced by
> automated tests.

## Why this exists

CLI invocations in documentation are shell commands (`bash` fenced blocks),
not `python` code blocks, so the [doc-example testing](doc-example-testing.md)
rule deliberately skips them — until this standard, they were validated by
nothing at all.

**robotsix-config** shows the failure mode this standard prevents. The README
documents

```bash
roboticsix-config schema myapp.config:Settings
```

but the parser splits the dotted path on the last dot
(`dotted_path.rpartition(".")`), so the colon ends up inside the attribute
name and the import fails. The module docstring even warns that the
`module:Class` form does not work — yet the README kept showing it. Every
user who follows the documented example hits an ImportError with a confusing
message that never points back at the docs.

## The rule

Every Python repository that documents CLI command invocations must satisfy
all three of:

1. **Documented invocations match the parser.** Every CLI example in public
   documentation must use exactly the argument syntax the real parser
   accepts — flags, positionals, value formats, and dotted-path forms.
   **Failure mode:** a documented example that contradicts the parser makes
   every user who follows it hit a runtime error; the error text rarely
   names the docs, so the library takes the blame.

2. **Documented invocations are tested.** The package must include hermetic
   tests that execute the documented command lines verbatim as subprocesses
   against the installed console script and assert success. The documented
   command should appear in the test unchanged, so a docs/parser mismatch is
   a red test, not a user bug report. **Failure mode:** without these tests,
   a parser change that breaks a documented form (or a doc edit that invents
   one) ships with no CI signal.

3. **CI runs the validation.** The CLI-example tests run as part of the
   standard test gate, so a PR that changes the parser or the docs cannot
   merge with stale examples. **Failure mode:** a validation step that is
   not in CI drifts until a user reports the exact ImportError it was meant
   to prevent.

## How to validate documented examples

For each documented invocation, one test runs the exact command through the
installed console script as a subprocess and asserts exit code 0. Follow the
skip-guard pattern from [console-script subprocess
tests](console-script-subprocess-test.md) so the suite still passes in
bare-dev environments where the script is not on `PATH`:

```python
"""Every CLI invocation shown in the README must run as documented."""

import shutil
import subprocess

import pytest

# One entry per documented example — keep this list in lockstep with the docs.
DOCUMENTED_INVOCATIONS = [
    ["roboticsix-config", "schema", "myapp.config.Settings"],
    ["roboticsix-config", "schema", "myapp.config.Settings", "--format", "json"],
]


@pytest.mark.skipif(
    shutil.which("roboticsix-config") is None,
    reason="console script not installed",
)
@pytest.mark.parametrize("argv", DOCUMENTED_INVOCATIONS)
def test_documented_cli_example(argv: list[str]) -> None:
    """A documented CLI example must be a valid invocation of the real CLI."""
    result = subprocess.run(argv, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"documented example {' '.join(argv)} fails: {result.stderr}"
    )
```

The documented command line lives in the test as-is, so a doc edit that
introduces a form the parser rejects (like the colon form above) immediately
fails the parametrized test.

## Side effects

CLI examples that write files or hit the network must stay hermetic: run them
under `tmp_path` and mock outbound calls exactly as [doc-example
testing](doc-example-testing.md#hermetic-execution) requires. **Failure
mode:** a validation test that writes into the repo tree or calls a real
endpoint is flaky in CI and corrupts parallel test workers.

## Cross-reference

- **[Doc-example testing](doc-example-testing.md)** — runnable `python` code
  blocks in docs; the doc-quality sibling of this standard.
- **[Console-script subprocess tests](console-script-subprocess-test.md)** —
  the subprocess invocation pattern and `shutil.which` skip guard this
  standard builds on.
