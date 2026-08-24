# Secret files are never tracked

> **Scope: every robotsix repository.** A mandatory `.secrets-patterns-excluded`
> file (not `.gitignore`) tells TruffleHog and detect-secrets which paths to
> skip — so the scanners don't waste time on directories that never contain
> secrets, and so a false positive in a known-safe file can be suppressed
> without weakening the repo's `.gitignore` deny list.

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

Every repo ships a `.secrets-patterns-excluded` file at the repo root. It
lists one glob pattern per line, in the syntax that both TruffleHog and
detect-secrets accept. The file is version-controlled and reviewed — adding a
pattern is a deliberate decision, not a side effect of a local tool run.

## File format

One glob pattern per line. Blank lines are ignored. Lines starting with `#`
are comments.

```text
# Directories that never contain secrets — skip them entirely.
tests/fixtures/*
docs/examples/*
# Large vendored test data that triggers high-entropy false positives.
vendor/*
```

Patterns follow [gitignore-style glob
syntax](https://git-scm.com/docs/gitignore#_pattern_format):

- `*` matches anything except `/`.
- `**` matches anything including `/`.
- A trailing `/` matches only directories.
- A leading `/` anchors to the repo root; otherwise the pattern matches
  anywhere in the tree.

## Where it lives

**Repo root** — the same directory as `.gitignore`, `.pre-commit-config.yaml`,
and `pyproject.toml`. Both `detect-secrets` (via the `--exclude-files` flag in
`.pre-commit-config.yaml`) and TruffleHog (via the `--exclude-paths` flag in
the CI workflow) read it from this location.

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

### detect-secrets (pre-commit hook)

The `.pre-commit-config.yaml` entry passes the file to detect-secrets via the
`--exclude-files` flag:

```yaml
- repo: https://github.com/Yelp/detect-secrets
  rev: v1.5.0
  hooks:
    - id: detect-secrets
      args:
        - '--exclude-files'
        - '.secrets-patterns-excluded'
        - '--baseline'
        - '.secrets.baseline'
```

detect-secrets reads the file, expands each glob, and skips matching paths
during its working-tree scan.

### TruffleHog (CI)

The shared security workflow passes the file to TruffleHog via the
`--exclude-paths` flag:

```bash
trufflehog filesystem --exclude-paths .secrets-patterns-excluded .
```

TruffleHog reads the file, expands each glob, and skips matching paths during
its filesystem scan. The same flag works for `trufflehog git` (full-history
scan) — the patterns apply to the checked-out tree, not to historical paths.

## Failure prevented

Without `.secrets-patterns-excluded`, a repo has two bad options when a
scanner produces a false positive on a tracked file:

1. **Add the file to `.gitignore`** — the file stops being tracked, breaking
   CI and local development.
2. **Accept the false positive** — every scan run flags it, training
   contributors to ignore scan output.

With `.secrets-patterns-excluded`, the file stays tracked and the scanner
stays quiet. Each pattern addition is reviewed in a PR, so a pattern that
accidentally excludes a real credential file is caught before it merges.

## See also

- [Security posture — gate 5 (Secret push protection)](security-posture.md#5-secret-push-protection)
- [Repo baseline — CI and security gates](repo-baseline.md#ci-and-security-gates)
