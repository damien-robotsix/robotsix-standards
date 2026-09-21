# Secret files are never tracked

> **Scope: every robotsix repository.** A mandatory `.secrets-patterns-excluded`
> file (not `.gitignore`) is the single reviewed record of paths the secret
> scanners skip. TruffleHog reads it directly; detect-secrets' own exclusion
> config is kept in sync with it — so the scanners don't waste time on
> directories that never contain secrets, and so a false positive in a
> known-safe file can be suppressed without weakening the repo's `.gitignore`
> deny list.

Secret scanning (gate 5 of [security posture](security-posture.md)) catches
*detected* secrets — API keys, tokens, high-entropy strings — but not all
credential-shaped files. An `.htpasswd` holds a bcrypt hash (no cleartext
pattern for a scanner to match), a `wp-config.php` may template its
credentials, and private-key files only match when the scanner recognises the
format. The defense for those files is a deny list (`.gitignore` — see gate 5
for the minimum patterns). The companion defense for the *scanners themselves*
is `.secrets-patterns-excluded` — a separate exclusion file so the scanners
can be told to skip directories and files that are known-safe without altering
what git tracks.

## The rule

Every repo ships a `.secrets-patterns-excluded` file at the repo root. It lists
one regular expression per line — the format TruffleHog's `--exclude-paths`
flag parses. The file is version-controlled and reviewed — adding a pattern is
a deliberate decision, not a side effect of a local tool run.

## File format

One regular expression per line. Blank lines are ignored. Lines starting with
`#` are comments. Each pattern is matched against a file's path.

```text
# Directories that never contain secrets — skip them entirely.
^tests/fixtures/
^docs/examples/
# Large vendored test data that triggers high-entropy false positives.
^vendor/
```

The patterns are [RE2 / Go regular
expressions](https://github.com/google/re2/wiki/Syntax) (TruffleHog is written
in Go); the common subset also compiles under Python's `re`, which is what the
enforcement gate (below) uses to validate each line. Anchor with `^` to match
from the start of a path, use `.*` for "match anything", and escape a literal
dot as `\.`. This is **not** gitignore-glob syntax — a bare `*` is a
quantifier, not a wildcard, so a glob such as `*secret*` is not a valid regex
and the gate rejects it (a directory prefix is `^vendor/`, not `vendor/*`).

## Where it lives

**Repo root** — the same directory as `.gitignore`, `.pre-commit-config.yaml`,
and `pyproject.toml`. TruffleHog reads it from this location via the
`--exclude-paths` flag (the CI workflow); detect-secrets' exclusions (see
below) are configured in `.pre-commit-config.yaml`, which lives in the same
directory.

## How it interacts with `.gitignore`

`.secrets-patterns-excluded` is **not** `.gitignore`. The two files serve
different purposes and must not be merged:

| File | Purpose | Effect |
|---|---|---|
| `.gitignore` | Tells git which files to never track. | A file matching a `.gitignore` pattern cannot be committed (unless force-added). |
| `.secrets-patterns-excluded` | Tells secret scanners which paths to skip. | A file matching a pattern is still tracked and version-controlled; it just isn't scanned for secrets. |

Examples of files that belong in `.secrets-patterns-excluded` but **not** in
`.gitignore`:

- **Test fixtures** containing synthetic keys (`tests/fixtures/fake-certs/`).
  These are version-controlled so CI can run the same tests, but scanning them
  produces false positives.
- **Vendored third-party code** (`vendor/` or `third_party/`). The code is
  tracked, but secret-scanning it is the upstream's responsibility.
- **Documentation examples** that embed placeholder credentials
  (`docs/examples/config-with-placeholder-key.yaml`). The file is tracked and
  reviewed, but the placeholder triggers scanners.

Examples of files that belong in `.gitignore` but **not** in
`.secrets-patterns-excluded`:

- A production `.env` file (`*.env`). It must never be tracked; a scanner
  exclusion is irrelevant because the file shouldn't exist in the working tree
  at all.
- Private key files (`*.pem`, `*.key`). Same reasoning — they must never be
  committed.

## How the scanners consume it

The two scanners take path exclusions in different ways. Only TruffleHog reads
`.secrets-patterns-excluded` directly; detect-secrets does not read any pattern
file, so its exclusions are configured separately and kept in sync with it.

### TruffleHog (CI)

The shared security workflow passes the file to TruffleHog via the
`--exclude-paths` flag:

```bash
trufflehog filesystem --exclude-paths .secrets-patterns-excluded .
```

TruffleHog reads the file, compiles each line as a regular expression, and
skips paths that match during its filesystem scan. The same flag works for
`trufflehog git` (full-history scan) — the patterns apply to the checked-out
tree, not to historical paths.

### detect-secrets (pre-commit hook)

detect-secrets does **not** read `.secrets-patterns-excluded`. Its
`--exclude-files` flag takes a **single regular expression** matched against
file paths — not a path to a file of patterns. Passing the filename
(`--exclude-files .secrets-patterns-excluded`) is a silent no-op: detect-secrets
treats the literal string as a regex, matches it against nothing useful, and
never opens the file. The globs the file lists are therefore ignored, and the
pre-commit-layer exclusion the standard promises never happens.

Configure detect-secrets' path exclusions with the mechanisms it actually
supports, kept in sync with `.secrets-patterns-excluded`:

- the pre-commit hook's own `exclude:` regex (a pre-commit-native file filter), and
- the `.secrets.baseline` (which records reviewed findings per file).

```yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.5.0
  hooks:
    - id: detect-secrets
      args:
        - '--baseline'
        - '.secrets.baseline'
      # Path exclusions go here as a single regex, mirroring
      # .secrets-patterns-excluded — NOT `--exclude-files <that file>`.
      exclude: '\.secrets\.baseline$'
```

## How this is enforced

`scripts/check-secrets-patterns-excluded.py` (the
`secrets-patterns-excluded-check` job in
`.github/workflows/baseline-check.yml`) makes the rule mechanically checkable.
It verifies that:

- `.secrets-patterns-excluded` exists at the repo root;
- every non-comment line compiles as a regular expression (a gitignore-style
  glob such as `*secret*` fails this check); and
- `.pre-commit-config.yaml` does not wire the file into detect-secrets via the
  no-op `--exclude-files .secrets-patterns-excluded` form.

Like the `.gitignore` deny-list gate, it is **warning-first** (2026-09): it
emits `::warning::` annotations but does not fail the build, so the fleet can
converge before a follow-up gate flips it to fail-closed.

## Failure prevented

*Failure mode 1 — silent no-op wiring.* Feeding the glob file to detect-secrets
via `--exclude-files` (which expects a regex, not a file) silently ignores
every pattern in it: the promised pre-commit exclusion never runs and nobody
notices, because a no-op produces no error. The enforcement gate above catches
that exact miswiring.

*Failure mode 2 — false positives with no safe escape.* Without a reviewed
exclusion file, a repo has two bad options when a scanner flags a tracked file:

1. **Add the file to `.gitignore`** — the file stops being tracked, breaking
   CI and local development.
2. **Accept the false positive** — every scan run flags it, training
   contributors to ignore scan output.

With `.secrets-patterns-excluded`, the file stays tracked and the scanner stays
quiet. Each pattern addition is reviewed in a PR, so a pattern that accidentally
excludes a real credential file is caught before it merges.

## See also

- [Security posture — gate 5 (Secret push protection)](security-posture.md#5-secret-push-protection)
- [Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)
