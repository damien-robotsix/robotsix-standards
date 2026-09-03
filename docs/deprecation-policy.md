# Deprecation lifecycle

> **Scope: every Python library with a public API.** A public library removes
> an API only after it has shipped at least one release cycle marked as
> deprecated — announced in the docstring, emitted at runtime as a
> `DeprecationWarning`, and signalled in the changelog — so a consumer gets a
> migration window instead of a break with no notice.

## Why this exists

Fleet libraries version with [release-please](release-please.md) and
conventional commits: a `BREAKING CHANGE:` footer bumps the major version and
lands the removal in the changelog. That mechanism is binary — an API is
supported until the release where it is deleted, with no intermediate phase.

Without a deprecation phase between "supported" and "removed":

- A library removes an API with no advance notice, forcing every consumer to
  update in lockstep with the major release.
- A consumer cannot tell "still works, but plan ahead" from "gone, act now" —
  both arrive as a breaking release.
- Nothing shows up in the consumer's own test run before the removal, so the
  break is discovered only after upgrading.

This standard adds the missing phase: an API is first marked deprecated (it
still works and still passes tests, but warns), and is removed no earlier than
the next major release. Consumers get a release cycle to migrate, and a runtime
signal they can catch in CI.

## The lifecycle (mandatory)

**Deprecate in version N; remove no earlier than the next major release.** A
public API that is going away must first ship a release in which it is marked
deprecated but still functions. Its removal lands in a later major release —
never in the same release that first deprecates it.

*Failure prevented:* deprecating and removing in the same release gives the
consumer zero migration window — the deprecation notice and the break arrive
together, which is exactly the no-notice removal this standard exists to
prevent.

## Runtime warning (mandatory)

A deprecated callable emits a `DeprecationWarning` via `warnings.warn` on use,
naming the replacement and the version in which removal is planned:

```python
import warnings


def old_function(x):
    """Compute the widget total.

    .. deprecated:: 0.7.0
        Use :func:`new_function` instead. Will be removed in 1.0.0.
    """
    warnings.warn(
        "old_function() is deprecated since 0.7.0 and will be removed in "
        "1.0.0; use new_function() instead.",
        DeprecationWarning,
        stacklevel=2,
    )
    return new_function(x)
```

- Use `DeprecationWarning` (not `UserWarning` or a bare `print`) so consumers
  can filter, silence, or escalate it through the standard `warnings`
  machinery.
- Pass `stacklevel=2` so the warning points at the **caller's** line, not the
  line inside the deprecated function — a warning that blames the library's own
  source tells the consumer nothing about where to fix their code.

*Failure prevented:* an API that is documented as deprecated but emits no
runtime warning is invisible to a consumer who does not re-read the changelog —
the deprecation cannot surface in their test run, so the first signal they get
is the removal.

## Docstring convention (mandatory)

Mark the deprecated object with a reStructuredText `.. deprecated::` block (as
above) naming the version it was deprecated in, the replacement, and the
version in which it will be removed. This follows the fleet
[docstring convention](docstrings.md) and renders as a highlighted admonition
in the built docs.

*Failure prevented:* a deprecation recorded only in a commit message or a
changelog entry is not visible at the point of use — a developer reading the
API reference or their editor's hover tooltip sees no signal that the function
is on its way out.

## Changelog signal (mandatory)

Ship the deprecation in a conventional commit (`feat:`, `fix:`, or `refactor:`
as appropriate) and add a `Deprecation:` footer — analogous to
`BREAKING CHANGE:` — naming the deprecated API and its planned removal version:

```text
refactor: route widget totals through new_function

Deprecation: old_function() is deprecated as of this release and will be
removed in 1.0.0. Use new_function() instead.
```

The `Deprecation:` footer is a greppable marker across history that lets a
maintainer enumerate outstanding deprecations and confirm each is removed on
schedule. The matching `BREAKING CHANGE:` footer is added by the later commit
that performs the removal, so [release-please](release-please.md) records the
removal as the major-version-bumping changelog entry.

*Failure prevented:* a deprecation that leaves no durable trail in history
cannot be audited — no one can answer "which deprecated APIs are due for
removal in the next major?" without reading every docstring by hand.

## Testing (mandatory)

Add a test that asserts the deprecated API both **still works** and **emits a
`DeprecationWarning`**:

```python
import pytest


def test_old_function_warns_and_works():
    with pytest.warns(DeprecationWarning, match="removed in 1.0.0"):
        result = old_function(2)
    assert result == expected  # still functions during the deprecation window
```

The fleet [pytest practices](pytest.md) set `filterwarnings = ["error"]`, which
turns every un-asserted warning into a test failure. A `pytest.warns` block
is therefore required: it both proves the warning fires and scopes the
error-on-warning filter so the deprecated call does not fail the suite.

*Failure prevented:* without a test, the `warnings.warn` call can be dropped in
a refactor with nothing to catch it, and the deprecation silently stops warning
before the API is removed — reopening the no-notice-removal gap.

## Companion standards

- **[Release-please release automation](release-please.md)** — the
  conventional-commit + `BREAKING CHANGE:` mechanism this policy layers a
  deprecation phase on top of.
- **[Docstring convention](docstrings.md)** — the docstring style the
  `.. deprecated::` block conforms to.
- **[Pytest practices](pytest.md)** — the `filterwarnings = ["error"]` setting
  that makes the `pytest.warns` assertion mandatory.
- **[Single-source versioning](single-source-versioning.md)** — the version
  string a deprecation notice references for its "deprecated since" and
  "removed in" versions.
