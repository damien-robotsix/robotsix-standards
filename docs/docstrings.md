# Docstring convention

> **Scope: every Python repository.** These rules apply to all public
> modules, classes, and functions across the fleet.

## Style

**Google-style docstrings** — `Args:`, `Returns:`, `Raises:` sections —
are the fleet standard for all Python docstrings.

```python
def connect(host: str, port: int = 443, *, timeout: float = 30.0) -> Connection:
    """Open a TLS connection to *host*.

    Args:
        host: The remote hostname or IP address.
        port: TCP port (default 443, the standard TLS port).
        timeout: Connection timeout in seconds.

    Returns:
        A ready-to-use ``Connection`` object.

    Raises:
        ConnectionError: If the TCP handshake or TLS negotiation fails.
        ValueError: If *port* is zero or negative.
    """
```

## Why Google style

The fleet's documentation toolchain uses **mkdocstrings** to render API
reference pages from docstrings.  mkdocstrings defaults to the **Google
parser** — it expects `Args:` / `Returns:` / `Raises:` sections, not the
NumPy-style `Parameters` / `Returns` / `Raises` tables.  When a NumPy-style
docstring hits the Google parser, the parameter descriptions, return type,
and raised exceptions are **silently dropped** from the built docs — the
sections render as empty or are omitted entirely with no build warning.

NumPy-style docstrings are valid Python and pass every linter, so this
failure mode is invisible until someone reads the docs site and notices
missing content.  Standardising on Google style prevents the silent-drop
failure across the fleet.

## Requirements

- Every **public module**, **public class**, and **public function** MUST
  have a docstring.
- Public functions that accept parameters MUST include an `Args:` section
  documenting every parameter.
- Public functions that return a value MUST include a `Returns:` section.
- Sections MUST follow the Google style: `Args:`, `Returns:`, `Raises:` (not
  NumPy-style `Parameters`, `Returns`, `Raises`).

*Failure prevented:* a public function with a `timeout` parameter but no
`Args:` block renders with a blank parameter table on the docs site; mkdocstrings
cannot generate documentation for a parameter it cannot find in the docstring.

## Enforcement

Ruff's pydocstyle rules (`D`) enforce the convention at lint time.
Enable them in every Python repo's `pyproject.toml`:

```toml
[tool.ruff.lint]
extend-select = ["D"]
ignore = ["D105", "D107", "D205", "D415"]

[tool.ruff.lint.pydocstyle]
convention = "google"

[tool.ruff.lint.per-file-ignores]
"tests/**" = ["D"]
"docs/**" = ["D"]
```

- **`extend-select = ["D"]`** enables the full pydocstyle rule set on top of
  whatever rules the repo already selects.  This is preferred over `select
  = ["...", "D100", "D101", ...]` because the `D` prefix pulls in every
  pydocstyle rule now and any future rules ruff adds under `D` —
  no manual update needed.
- **`ignore`** suppresses four noisy rules:

  | Rule | Reason |
  |------|--------|
  | `D105` | `__init__` methods are self-documenting by their parameters |
  | `D107` | Already covered by the class docstring |
  | `D205` | Conflicts with `D400` (first-line period); `D400` takes precedence |
  | `D415` | Google style allows non-imperative first lines for some sections |

- **`per-file-ignores`** exempts `tests/` and `docs/` from docstring
  enforcement — tests are self-documenting, and docs are prose.

The `convention = "google"` setting tells pydocstyle to expect `Args:`,
`Returns:`, and `Raises:` section headers (not NumPy-style `Parameters`
etc.), so rule D417 checks for argument documentation in the correct
format.
