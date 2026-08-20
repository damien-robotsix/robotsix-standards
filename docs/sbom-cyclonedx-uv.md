# CycloneDX SBOM via `uv export`

> **Scope: every robotsix repository with a `uv.lock` file that publishes or
> uploads an SBOM in CI.** Repos that do not generate an SBOM (content-only
> docs repos, pure-static sites) are unaffected.

## Why this exists

Before this standard, several fleet repos emitted an SBOM via:

```yaml
- name: Generate SBOM
  run: uv audit --frozen --output-format json > sbom.json || true
```

`uv audit --output-format json` produces a **vulnerability/advisory report** —
OSV advisory matches, severities, affected and fixed ranges. It is not a
Software Bill of Materials. It contains no standards-conformant component
inventory, so the artifact cannot be consumed by intended downstream tooling:

- Dependency-Track (expects CycloneDX or SPDX)
- GitHub dependency graph submission (`dependency-graph` action)
- `grype`, `trivy sbom`, or similar container/machine-image scanners
- VEX and procurement pipelines that require a conformant BOM

The artifact is misnamed: calling advisory output `sbom.json` trains
reviewers and automation to treat audit output as an SBOM, which silently
blocks any consumer from receiving an actual inventory.

**Failure mode:** a compliance audit or procurement review requires an SBOM;
the repo provides a vulnerability report. The consumer rejects it as
non-conformant, creating a blocking compliance gap that must be resolved
ad-hoc (often by hand-generating a CycloneDX document) rather than
automatically from the existing lockfile.

## The rule

Every uv-based repo that publishes or uploads an SBOM in CI **must** generate
a standards-conformant CycloneDX document natively from the lockfile:

```yaml
- name: Generate SBOM
  run: uv export --frozen --format cyclonedx1.6+json --no-emit-project -o sbom.cdx.json
```

- **`--frozen`** — reads `uv.lock` as-is; does not re-resolve. Ensures the
  SBOM matches the exact pinned dependency set used in CI.
- **`--format cyclonedx1.6+json`** — emits CycloneDX 1.6 JSON, the latest
  standard version that uv supports natively.
- **`--no-emit-project`** — omits the project itself from the SBOM
  (CycloneDX metadata). The project is the consuming entity, not a component
  of its own supply chain; omitting it avoids a self-referential entry that
  some consumers reject as invalid.
- **`-o sbom.cdx.json`** — the `.cdx.json` extension signals that this is a
  CycloneDX document, distinguishing it from a JSON vulnerability report or
  a `requirements.txt`-style lock export.

**Failure mode (wrong format flag):** `--format cyclonedx` without the
version suffix emits CycloneDX 1.5, which uv supports but which some
consumers (e.g. Dependency-Track < 4.12) handle with reduced schema
validation. Pinning to `1.6+json` is forward-compatible and avoids version
ambiguity.

### Audit output is a separate artifact

The vulnerability audit report (`uv audit`) is a distinct artifact with a
different schema and purpose. It must be kept **separate** from the SBOM and
named accurately — for example `audit-report.json` — so consumers can
distinguish "this is the inventory" from "these are the known vulnerabilities
in that inventory":

```yaml
- name: Vulnerability audit
  run: uv audit --frozen --output-format json > audit-report.json || true
```

The `|| true` guard is appropriate for an advisory audit that should not
block the workflow on a newly published CVE; the CycloneDX SBOM step
omits `|| true` because a failed SBOM generation is a hard infrastructure
failure (bad lockfile, missing metadata) and should fail the job.

**Failure mode:** combining audit and SBOM into one step or one artifact
name (`sbom.json`) makes it impossible for downstream tooling to
distinguish the two. A dependency-track ingestion that receives a
vulnerability report instead of an SBOM silently produces an empty
component inventory — no alerts, no warnings, just no data.

### Artifact upload

The SBOM artifact follows the shared security-audit workflow pattern:

```yaml
- uses: actions/upload-artifact@v4
  with:
    name: sbom-cdx
    path: sbom.cdx.json
```

The artifact name (`sbom-cdx`) is distinct from any other SBOM artifact a
repo might publish (e.g. a container-image SBOM from syft or `grype`),
preventing upload-name collisions in multi-artifact workflows.

### No extra tooling required

CycloneDX SBOM export is native to uv (`uv export --format cyclonedx1.6+json`).
No additional tool (cyclonedx-py, syft, or trivy) is required for a
lockfile-based SBOM. This keeps CI bootstrapping minimal — `setup-uv`
already manages the uv binary that runs every other step.

## Cross-reference with security posture standard

The [security posture standard](security-posture.md) lists SBOM generation
as part of the required security gates (gate 5, secret protection and
supply-chain artifacts). The `uv export` command defined on this page is the
canonical implementation of that gate for uv-based repos.

**Failure mode:** two pages prescribing different SBOM commands (one via
`uv audit`, one via `uv export`) forces each repo to guess which is
canonical. This page is the single source of truth for lockfile-based SBOM
generation in uv repos; the security posture standard delegates to it rather
than repeating the command.

## Vulnerability audit is not an SBOM

| Property | `uv audit --output-format json` | `uv export --format cyclonedx1.6+json` |
|---|---|---|
| Schema | OSV advisory response | CycloneDX 1.6 BOM |
| Contents | Matching vulnerabilities (CVE/OSV id, severity, affected ranges) | Component inventory (name, version, purl, dependency graph) |
| Consumable by | Custom audit dashboards, advisory feeds | Dependency-Track, GitHub Dependabot, grype, trivy sbom, VEX pipelines |
| Standards body | OpenSSF / OSV | OWASP CycloneDX |
| CI exit on error | Advisory (`|| true` recommended) | Hard failure (must stop if SBOM cannot be produced) |

The two artifacts play complementary roles in supply-chain security: the
SBOM tells you **what you have**; the audit tells you **what is known wrong
with it**. Naming them identically (`sbom.json`) collapses two distinct
signals into one.

## Source

- [uv docs: CycloneDX SBOM export format](https://docs.astral.sh/uv/concepts/projects/export/#cyclonedx-sbom-format)
- Mature uv/Python projects (FastAPI, Pydantic, httpx, mypy) generate
  CycloneDX via `uv export`/`cyclonedx-py` or attach a syft-generated SBOM
  to releases — none reuse the audit output as an SBOM.
