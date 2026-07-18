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

## Enforcement

Ruff's pydocstyle rules (`D`) enforce the convention at lint time.
Enable the following rules in every Python repo's `pyproject.toml`:

```toml
[tool.ruff.lint]
select = [
    # ... existing rules ...
    "D100",   # public module missing docstring
    "D101",   # public class missing docstring
    "D103",   # public function missing docstring
    "D400",   # first line must end with a period
    "D412",   # no blank line between section header and content
    "D413",   # missing blank line after last section
    "D414",   # section has no content
    "D417",   # missing argument description
]

[tool.ruff.lint.pydocstyle]
convention = "google"
```

The `convention = "google"` setting tells pydocstyle to expect `Args:`,
`Returns:`, and `Raises:` section headers (not NumPy-style `Parameters`
etc.), so rule D417 checks for argument documentation in the correct
format.
