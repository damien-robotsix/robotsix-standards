# REUSE compliance and SPDX headers

> **Scope: every robotsix repository that tracks source files** — Python
> packages, shell scripts, YAML/CI configs, Dockerfiles, and Markdown docs.
> Pure content repos (this standards site included) still track source files,
> so the same rules apply there.

## Why this exists

The fleet's licensing story ends at the [repo baseline](repo-baseline.md)'s
License rule: a MIT `LICENSE` file at the repo root. That declares the
project's license once, but it is not machine-readable *per file* — a tool asked
"what license covers `scripts/backup.sh`?" must guess that the root `LICENSE`
applies and that every file is original fleet code. REUSE
([reuse.software](https://reuse.software)) closes that gap: a standardized
machine-readable copyright-and-licensing convention maintained by the Free
Software Foundation ecosystem and adopted by FSF/GNU projects (GNU Guix,
GNU Taler) and CNCF projects (Kubernetes, containerd).

**Failure mode:** a compliance audit, SBOM consumer, or downstream
redistribution check asks which license covers a specific file and no tool can
answer without a human reading the root `LICENSE` and guessing. Every consumer
re-implements that guess differently, and licensing drift — a vendored file
under a different license, a new file with no declaration — ships silently
because nothing checks.

## The rule

Every robotsix repository **must** make its licensing machine-readable and
enforced:

1. **`LICENSES/` directory** — the full text of each license in use, one file
   per SPDX identifier, copied verbatim from
   [spdx.org/licenses](https://spdx.org/licenses/) (e.g. `LICENSES/MIT.txt`).
2. **`.reuse/dep5`** — project-level default policy declaring MIT for all files
   that carry no individual annotation.
3. **SPDX headers** — `SPDX-FileCopyrightText` and `SPDX-License-Identifier` on
   every tracked source file.
4. **`reuse lint` in CI** — a blocking gate on every pull request.

`reuse` is available without modifying the repo (e.g. `uv tool run reuse lint`,
or `pipx run reuse lint`), so the CI step needs no bootstrapping.

### LICENSES/

Each license a repo uses gets its full reference text at `LICENSES/<SPDX
identifier>.txt`; the fleet default is `LICENSES/MIT.txt`. Do not hand-edit the
text — copy the SPDX reference text so the file matches what `reuse lint`
expects byte-for-byte.

**Failure mode:** without the matching text, `reuse lint` cannot resolve a
header's license identifier and fails; redistributed copies also lack the
license text recipients are entitled to.

### `.reuse/dep5`

The project-level default policy covers every file that cannot or does not
carry an individual header (JSON configs, generated files, binary assets). The
minimal form for a fleet repo:

```text
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Files: *
Copyright: 2026 Robotsix contributors
License: MIT
```

`License: MIT` refers to `LICENSES/MIT.txt`; the `Files: *` stanza makes the
default explicit so `reuse lint` never sees an "uncovered file" for a licensed
MIT file.

**Failure mode:** without a default policy, files that cannot carry comments
(JSON, binaries, generated output) have no way to declare their license, so the
repo either exempts them from the policy (an invisible gap) or fails `reuse
lint` with no clean way to comply.

### SPDX headers

Every tracked source file declares copyright and license at the top, after any
shebang/encoding line:

```bash
#!/usr/bin/env bash
# SPDX-FileCopyrightText: 2026 Robotsix contributors
# SPDX-License-Identifier: MIT
```

```python
# SPDX-FileCopyrightText: 2026 Robotsix contributors
# SPDX-License-Identifier: MIT
```

```yaml
# SPDX-FileCopyrightText: 2026 Robotsix contributors
# SPDX-License-Identifier: MIT
name: ci
```

```markdown
<!-- SPDX-FileCopyrightText: 2026 Robotsix contributors -->
<!-- SPDX-License-Identifier: MIT -->
```

Headers are declarative, not literary: the copyright line names the body of
contributors, the identifier comes from the [SPDX license list](https://spdx.org/licenses/),
and both are stable. `reuse annotate` can add them mechanically:

```bash
reuse annotate --license MIT --copyright "Robotsix contributors" --year 2026
```

**Failure mode:** a file with no header and no `.reuse/dep5` coverage is
"licensed by assumption"; `reuse lint` reports it as having no license, which
is a hard failure once the CI gate exists — so a human must retroactively
decide who owns an unmarked file.

### CI gate

`reuse lint` runs as a blocking step in the shared CI workflow, the same way
other lint gates do:

```yaml
- name: REUSE compliance
  run: uv tool run reuse lint
```

The full workflow caller template ships with the other workflow templates —
standards pages do not embed workflow YAML, so the exact step wiring lives
there. The step runs on every push and pull request and must fail the job;
advisory `|| true` is never used here, because an unlicensed file is a
compliance defect, not a transient condition.

**Failure mode:** without the gate, a pull request that adds an unlicensed or
mislabelled file goes green, and compliance is discovered exactly once — at
audit time, when the fix is expensive and touches files the original author
cannot identify.

## Adoption

The fleet does not use REUSE today: repos ship the root `LICENSE` and
nothing else (this page is written for them). Adopting repos land the four
pieces in one change — `LICENSES/MIT.txt`, `.reuse/dep5`, the per-file headers,
and the CI step — after running `reuse lint` locally until it passes. The
`reuse annotate` command exists exactly to make that bulk pass mechanical.

## Source

- [REUSE specification](https://reuse.software/spec/)
- [SPDX license list](https://spdx.org/licenses/)
- FSF/GNU projects (GNU Guix, GNU Taler) and CNCF projects (Kubernetes,
  containerd) use REUSE for machine-readable licensing; this page's rule set
  follows their file-level practice.
