# py.typed wheel guard

> **Scope: every type-aware (PEP 561-typed) Python repository.** This standard
> codifies how to automatically verify that the `py.typed` marker ships in the
> built wheel, so a packaging regression cannot silently strip type information
> from downstream consumers. It is *in addition to* the
> [Python practices](python.md) `py.typed` declaration rule and the
> [distribution & packaging](distribution-packaging.md) git-based consumption
> model.

The [Python practices](python.md#project-layout) standard requires every
package to ship a `py.typed` marker (PEP 561), and every package must also
declare the `Typing :: Typed` trove classifier. But the marker's presence in
the **built wheel** is currently unverified across the fleet — nothing builds
the wheel and asserts the marker is inside it. A packaging regression (an
`only-include` glob that drops it, an accidental delete, a build-backend change)
silently strips type information from every downstream consumer with no warning.

## Rules

### 1. Downstream-consumption safety net (primary)

**Rule:** Every type-aware package's CI type-check MUST consume the
*installed/distributed* package rather than only the source tree, so a missing
`py.typed` marker surfaces as a loud type-check or import failure.

**Rationale:** This is the ecosystem norm — pydantic, anyio, httpx, and other
typed libraries rely on their own CI consuming the installed package as the
primary check that type metadata ships correctly. A source-tree-only mypy run
sees the marker on disk regardless of whether it made it into the wheel; the
installed check catches the gap.

The canonical way to implement this is a CI step that builds the wheel, installs
it in a clean venv, and runs mypy/pyright against a test file that imports the
package:

```yaml
- name: Build wheel
  run: uv build
- name: Install wheel in clean venv
  run: |
    uv venv /tmp/check-typed
    uv pip install --python /tmp/check-typed/bin/python dist/*.whl
- name: Verify type-check against installed package
  run: |
    echo "import robotsix_foo" > /tmp/check_import.py
    uv run --python /tmp/check-typed/bin/python mypy /tmp/check_import.py
```

> **Failure mode.** A CI pipeline that runs mypy against the source tree only
> (`uv run mypy src/`) will pass even when the `py.typed` marker is missing
> from the built wheel — the marker file sits on disk in the source tree and
> mypy has no way to know the wheel dropped it. The first consumer to install
> the broken wheel gets a silent type-check failure (or `# type: ignore`
> suppressions they don't understand).

### 2. Belt-and-suspenders wheel-content assertion

**Rule:** Every type-aware package's CI MUST include an explicit assertion that
the `py.typed` marker path exists inside the built wheel archive. This check
fails fast at packaging time, before any downstream type-checker run.

**Rationale:** A wheel-content assertion provides a direct, inspectable failure
message ("wheel missing py.typed") rather than a cryptic mypy error in a
separate CI job that a contributor must trace backwards. It also catches the
gap before the wheel is ever installed or type-checked against.

The check is a one-liner in Python:

```python
import zipfile, sys

wheel = sys.argv[1]
names = zipfile.ZipFile(wheel).namelist()
if "robotsix_foo/py.typed" not in names:
    raise SystemExit(f"{wheel}: missing py.typed marker")
```

Integrate it into CI as a step:

```yaml
- name: Assert py.typed in wheel
  run: uv run python -c "
    import zipfile, sys, glob
    wheels = glob.glob('dist/*.whl')
    assert wheels, 'no wheel found in dist/'
    names = zipfile.ZipFile(wheels[0]).namelist()
    assert 'robotsix_foo/py.typed' in names, f'{wheels[0]}: missing py.typed marker'
    print(f'{wheels[0]}: py.typed OK')
    "
```

> **Failure mode.** A build-backend upgrade that switches from hatchling to
> flit_core, or a `tool.hatch.build.targets.wheel.only-include` glob that
> accidentally omits `py.typed`, produces a wheel with no marker. Without the
> wheel-content assertion, the first signal is a downstream consumer filing an
> issue — often weeks later, when they upgrade and their type-check breaks.

### 3. Package name in the assertion must match the actual package

**Rule:** The wheel-content assertion MUST use the actual package import name
(e.g. `robotsix_foo/py.typed`), not a hard-coded placeholder. A single
`py.typed` glob that matches any package is acceptable as a fallback but the
primary assertion must be explicit, so a rename doesn't silently pass against
the old name.

**Rationale:** A hard-coded `my_package/py.typed` that survived a rename from
`my_package` to `robotsix_foo` would trivially pass (the old name is absent) or
trivially fail (the new name is absent) — in either case it doesn't verify the
intended package. An explicit name fails loudly when the package renames.

> **Failure mode.** A wheel-content check that asserts `src/py.typed` (the
> source-tree path) instead of `package_name/py.typed` (the installed path)
> will never match because wheel archives use the installed layout. The check
> always fails or always passes depending on the match logic — it provides no
> signal either way.

## Enforcement

The enforcement gate lives at `scripts/check-py-typed-guard.py` in the
standards repo.  Every type-aware (PEP 561) Python repository must invoke
it in CI — it exits non-zero when the repository declares itself typed
but neither guard rule is present in its workflow files.

### How to add the gate to your repository

Copy the script into your repository's `scripts/` directory (keep it in
sync with the upstream standards repo) and add a CI step:

```yaml
- name: Check py.typed wheel guard
  run: uv run python scripts/check-py-typed-guard.py
```

If the check fails the output tells you which guard is missing and how
to add it, referencing this standard page.

### What the script checks

1. **Is the package type-aware?**  It reads `pyproject.toml` for the
   `Typing :: Typed` trove classifier, and scans the source tree for
   a `py.typed` marker file (PEP 561).  If neither is present the
   check passes — no guard is required for untyped packages.

2. **Does CI include at least one guard?**  It scans every
   `.github/workflows/*.yml` file for either:
   - an **installed type-check** (build wheel → install in clean venv →
     run mypy/pyright against the installed package), or
   - a **wheel-content assertion** (zipfile inspection explicitly
     checking for `py.typed` inside the built wheel).

   If neither pattern is found the check fails with a diagnostic
   message that links back to this page.

> **Failure mode prevented.** A typed package whose CI workflow drifts
> away from the guard (e.g. a refactor that removes the installed-check
> step without replacing it) silently loses downstream type-safety. The
> enforcement gate catches the regression at PR time, before the wheel
> is published.
