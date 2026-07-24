# Python Makefile convention

> **Scope: every Python repository using uv.** The Makefile targets defined
> here give every repo the same self-documenting interface for common
> development tasks.

## Why this exists

Most fleet Python repos carry a `Makefile` with a handful of targets —
install, lint, test, clean — but the naming is inconsistent: one repo uses
`check-lock`, another uses `lock-check`; one has `test-unit`, another has
`unit-test`. Contributors moving between repos must re-learn the target names
each time. CI workflows that invoke `make <target>` break when the target
doesn't exist or does something unexpected.

A single documented convention eliminates that drift. Every repo that
conforms has the same targets, the same `.PHONY` discipline, and the same
`## Description` comments so a `help` target can self-document.

The convention is based on existing fleet practice — several repos already
follow most of it — so adoption is a rename, not a redesign.

## Required targets

All targets MUST be declared `.PHONY`. Every target MUST carry a `##
Description` comment immediately before the target line.

### `install`

```makefile
.PHONY: install
install: ## Install all dependencies (including dev)
    uv sync --all-extras
```

### `lint`

```makefile
.PHONY: lint
lint: ## Lint and format check
    uv run ruff check .
    uv run ruff format . --check
```

### `typecheck`

```makefile
.PHONY: typecheck
typecheck: ## Static type check
    uv run mypy src/ --strict | uv run --with mypy-baseline mypy-baseline filter
```

### `test`

```makefile
.PHONY: test
test: test-unit ## Run unit tests (default)
```

The default `test` target delegates to `test-unit`. CI and local `make test`
must not run integration tests, which require external services and are
unreliable in CI without setup.

### `test-unit`

```makefile
.PHONY: test-unit
test-unit: ## Run unit tests only (no integration)
    uv run pytest -m 'not integration' tests/
```

Runs tests that are not marked `@pytest.mark.integration`. See the
[pytest practices](pytest.md) page for marker registration and strictness
rules.

### `test-integration`

```makefile
.PHONY: test-integration
test-integration: ## Run integration tests only
    uv run pytest -m integration tests/
```

Runs only tests marked `@pytest.mark.integration`. These tests typically
require external services (databases, APIs) and are not run during CI unless
the workflow explicitly invokes `make test-integration`.

### `coverage`

```makefile
.PHONY: coverage
coverage: ## Run tests with coverage report
    uv run pytest --cov=src --cov-report=term-missing --cov-report=html tests/ -m 'not integration'
```

### `docs`

```makefile
.PHONY: docs
docs: ## Build documentation (strict mode)
    uv run --group docs mkdocs build --strict
```

### `lock-check`

```makefile
.PHONY: lock-check
lock-check: ## Verify uv.lock matches pyproject.toml
    uv lock --check
```

Validates that `uv.lock` is consistent with `pyproject.toml` without
re-resolving dependencies. This is a fast CI gate: a stale lockfile fails
the check rather than silently resolving to different versions at build time.

### `pre-commit`

```makefile
.PHONY: pre-commit
pre-commit: ## Run all pre-commit hooks
    uv run pre-commit run --all-files
```

Lets CI and developers run every pre-commit hook via a single `make`
invocation without remembering the `pre-commit` subcommand.

### `clean`

```makefile
.PHONY: clean
clean: ## Remove build artifacts and caches
    rm -rf build/ dist/ *.egg-info/ .eggs/
    rm -rf .pytest_cache/ .ruff_cache/
    rm -rf .mypy_cache/ .hypothesis/
    rm -rf site/ htmlcov/ .coverage*
    rm -rf __pycache__/ **/__pycache__/
    find . -type d -name .hypothesis -exec rm -rf {} +
```

Removes all generated artifacts, including:

| Artifact | Source |
|----------|--------|
| `build/`, `dist/`, `*.egg-info/`, `.eggs/` | setuptools/hatchling build |
| `.pytest_cache/`, `.ruff_cache/` | linter and test caches |
| `.mypy_cache/` | mypy incremental type-check cache |
| `.hypothesis/` | Hypothesis example database |
| `site/` | mkdocs build output |
| `htmlcov/`, `.coverage*` | coverage reports |
| `__pycache__/` | Python bytecode cache |

## Optional targets

### `coverage-view`

```makefile
.PHONY: coverage-view
coverage-view: ## Open coverage HTML report in browser
    xdg-open htmlcov/index.html || open htmlcov/index.html
```

Opens the coverage HTML report. Falls back from `xdg-open` (Linux) to
`open` (macOS).

### `test-op`

```makefile
.PHONY: test-op
test-op: ## Run a specific test path (usage: TEST_PATH=tests/test_foo.py make test-op)
    uv run pytest $(TEST_PATH)
```

A parameterized target for running specific test subsets. The caller sets
`TEST_PATH` to the desired test file or directory.

### `docs-serve`

```makefile
.PHONY: docs-serve
docs-serve: ## Serve documentation locally with live reload
    uv run --group docs mkdocs serve
```

## The `help` target

Every Makefile SHOULD include a self-documenting `help` target so developers
can discover available targets without reading the Makefile source:

```makefile
.PHONY: help
help: ## Show this help message
    @grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
      | sort \
      | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'
```

This grep-awk one-liner extracts every `## Description` comment and prints
a formatted table. It has no dependencies beyond `grep` and `awk`, which are
available on every runner.

## Full example

```makefile
# ==========================================================================
# Makefile — robotsix fleet convention (Python / uv)
# ==========================================================================
# Run `make help` to list available targets with descriptions.

.PHONY: help
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
	  | sort \
	  | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

.PHONY: install
install: ## Install all dependencies (including dev)
	uv sync --all-extras

.PHONY: lint
lint: ## Lint and format check
	uv run ruff check .
	uv run ruff format . --check

.PHONY: typecheck
typecheck: ## Static type check
	uv run mypy src/ --strict | uv run --with mypy-baseline mypy-baseline filter

.PHONY: test
test: test-unit ## Run unit tests (default)

.PHONY: test-unit
test-unit: ## Run unit tests only (no integration)
	uv run pytest -m 'not integration' tests/

.PHONY: test-integration
test-integration: ## Run integration tests only
	uv run pytest -m integration tests/

.PHONY: coverage
coverage: ## Run tests with coverage report
	uv run pytest --cov=src --cov-report=term-missing --cov-report=html tests/ -m 'not integration'

.PHONY: coverage-view
coverage-view: ## Open coverage HTML report in browser
	xdg-open htmlcov/index.html || open htmlcov/index.html

.PHONY: test-op
test-op: ## Run a specific test path (usage: TEST_PATH=tests/test_foo.py make test-op)
	uv run pytest $(TEST_PATH)

.PHONY: docs
docs: ## Build documentation (strict mode)
	uv run --group docs mkdocs build --strict

.PHONY: docs-serve
docs-serve: ## Serve documentation locally with live reload
	uv run --group docs mkdocs serve

.PHONY: lock-check
lock-check: ## Verify uv.lock matches pyproject.toml
	uv lock --check

.PHONY: pre-commit
pre-commit: ## Run all pre-commit hooks
	uv run pre-commit run --all-files

.PHONY: clean
clean: ## Remove build artifacts and caches
	rm -rf build/ dist/ *.egg-info/ .eggs/
	rm -rf .pytest_cache/ .ruff_cache/
	rm -rf .mypy_cache/ .hypothesis/
	rm -rf site/ htmlcov/ .coverage*
	rm -rf __pycache__/ **/__pycache__/
	find . -type d -name .hypothesis -exec rm -rf {} +
```
