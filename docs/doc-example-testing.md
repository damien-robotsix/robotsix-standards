# Doc-example testing

> **Scope: every Python repository whose MkDocs documentation contains
> runnable code blocks.** Quick-start, usage, and how-to pages that show
> `python` fenced code blocks importing or calling the package's public API
> must execute those blocks as part of the CI test suite. A rename or removal
> of a public symbol then breaks the build instead of silently leaving the
> docs wrong.

## Why this exists

Fleet packages share the same mkdocs + mkdocstrings documentation pattern —
auto-generated API reference plus hand-written quick-start and usage pages.
A quick-start snippet that imports a class or calls a function that no longer
exists is a recurring, cross-repo failure mode: the docs ship with stale
examples that confuse every new user and erode trust in the documentation.

Mature typed-Python libraries have already solved this:

- **pydantic** tests essentially all of its documentation code blocks with
  `pytest-examples`, failing CI when a doc snippet no longer imports or runs —
  this is why pydantic's docs stay in lockstep with the API across major
  versions.
- **FastAPI** keeps every documentation example as a real importable module
  under `docs_src/` and imports and exercises those modules from its test
  suite, so an example that stops working fails CI.

Codifying a single doc-example-testing convention (recommended tool +
hermetic-execution rule) lets every fleet repo adopt one shared approach
rather than inventing local variants.

## The rule

Every Python repository whose MkDocs documentation contains **runnable**
`python` fenced code blocks (quick-start, usage, how-to) **must** execute
those blocks as part of the CI test suite.

**Failure mode:** without doc-example testing, renaming or removing a public
symbol (class, function, constant) silently breaks the documentation — the
stale snippet ships to users, and the first signal is a confused user, not a
CI failure.

## Recommended tooling

Two pytest plugins collect and execute Markdown code blocks:

| Plugin | Collection method | Notes |
|---|---|---|
| [`pytest-markdown-docs`](https://github.com/JohnNilsson/pytest-markdown-docs) | Collects `python` fenced blocks from `.md` files via `--markdown-docs` flag. | Lightweight; no extra test files needed. |
| [`mktestdocs`](https://github.com/mktestdocs/mktestdocs) | `check_md_file` fixture runs code blocks from a single Markdown file. | Fine-grained control; pair one test function per doc page. |

Either plugin is acceptable. Pick one and use it consistently across the
fleet. `pytest-markdown-docs` is the lower-friction default for repos that
want whole-directory collection; `mktestdocs` is the choice when a repo needs
per-file test functions (e.g. to apply different fixtures to different pages).

### Installation

Add the chosen plugin to the `[dependency-groups] dev` group (see
[Python practices](python.md#packaging) for the canonical dev-tooling
placement):

```toml
[dependency-groups]
dev = [
    "pytest-markdown-docs",
    # — or —
    "mktestdocs",
    # ... existing dev/test dependencies ...
]
```

**Failure mode:** declaring the plugin in the unconditional `[project]
dependencies` ships it in the installed library or service image, bloating
the production install with a package nothing imports at runtime.

## Hermetic execution

Code blocks that import the package under test are safe to run as-is — they
only read the package's public API. Blocks that perform **filesystem or
network side effects** (writing files, making HTTP requests, reading
environment variables) must run under a hermetic fixture so they do not
touch the repo tree or leak state between tests.

### Autouse `chdir` fixture

Add an autouse fixture in `tests/conftest.py` that redirects the working
directory to `tmp_path` for every doc-example test:

```python
import os
import pytest

@pytest.fixture(autouse=True)
def _chdir_tmp_path(tmp_path: pytest.Path) -> None:
    """Run every test in a temporary directory so doc examples are hermetic."""
    os.chdir(tmp_path)
```

This fixture is scoped to the doc-example test session. If the repo already
has an autouse `chdir` fixture (e.g. for integration tests), reuse it — do
not stack multiple `chdir` fixtures.

**Failure mode:** without the `chdir` fixture, a doc-example code block that
writes a file (e.g. `open("output.json", "w")`) pollutes the repo tree —
the file appears as an untracked change, and parallel test workers corrupt
each other's output.

### Network isolation

Doc-example code blocks **must not** make real network requests. If a block
demonstrates an HTTP call, it must use a mock or stub (e.g. `respx` for
`httpx`, `responses` for `requests`). The `chdir` fixture above does not
provide network isolation — that is the responsibility of the code block's
author.

**Failure mode:** a doc example that calls a real API endpoint fails
intermittently in CI (network flakiness, rate limits, auth expiry) and
breaks the build for reasons unrelated to the code change.

## CI integration

The doc-example test gate runs as part of the standard `ci.yml` test job —
it is not a separate workflow. The test command already runs `pytest tests/`,
and the doc-example tests live alongside the regular test suite:

```bash
uv run pytest tests/ --cov=<pkg> --cov-report=xml --cov-report=term-missing
```

If the repo uses `pytest-markdown-docs`, add the `--markdown-docs` flag and
point it at the `docs/` directory:

```bash
uv run pytest tests/ --markdown-docs docs/ --cov=<pkg> --cov-report=xml
```

If the repo uses `mktestdocs`, the test functions are already collected by
the standard `pytest tests/` invocation — no extra flags needed.

### Shared reusable workflow

The fleet's shared `python-ci.yml` reusable workflow (in
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows))
runs `pytest tests/` by default. Repos that use `pytest-markdown-docs` must
pass the `--markdown-docs` flag via `addopts` in `[tool.pytest.ini_options]`
so the shared workflow picks it up without modification:

```toml
[tool.pytest.ini_options]
addopts = ["--strict-markers", "--markdown-docs", "docs/"]
```

Repos that use `mktestdocs` need no `addopts` change — the test functions
are collected normally.

**Failure mode:** adding `--markdown-docs` only to the standalone `ci.yml`
but not to `addopts` means local `pytest` runs skip doc examples — a
developer sees green locally but CI fails on the same commit.

## Which pages to test

Test every documentation page that contains runnable `python` code blocks
that import or call the package's public API. Typical candidates:

- Quick-start / getting-started page
- Usage / how-to pages
- README.md (if it contains runnable code blocks)

Do **not** test:

- Pages with `python` blocks that are illustrative pseudocode (not valid
  Python, or using placeholder names like `my_function()`).
- Pages with `python` blocks that demonstrate shell commands or config
  snippets (use `bash` or `toml` fences instead).
- API reference pages generated by mkdocstrings — those are already
  validated by the type-checker and test suite.

**Failure mode:** testing pseudocode blocks produces import errors or
`NameError`s that block CI for no real benefit — the blocks were never
meant to run.

## Full example

A minimal setup for a repo using `pytest-markdown-docs`:

**`pyproject.toml`** (additions):

```toml
[dependency-groups]
dev = [
    "pytest-markdown-docs",
    # ... existing dev dependencies ...
]

[tool.pytest.ini_options]
addopts = ["--strict-markers", "--markdown-docs", "docs/"]
```

**`tests/conftest.py`** (addition):

```python
import os

import pytest

@pytest.fixture(autouse=True)
def _chdir_tmp_path(tmp_path: pytest.Path) -> None:
    """Run every test in a temporary directory so doc examples are hermetic."""
    os.chdir(tmp_path)
```

**`tests/test_doc_examples.py`** (new file, only needed with `mktestdocs`):

```python
from pathlib import Path

import mktestdocs

DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"

def test_quickstart() -> None:
    mktestdocs.check_md_file(DOCS_DIR / "quickstart.md")
```

With `pytest-markdown-docs`, no test file is needed — the plugin collects
blocks automatically from the `--markdown-docs` target directory.
