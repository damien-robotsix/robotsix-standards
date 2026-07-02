# Repo baseline

> **Scope: every robotsix repository** — libraries and deployable components
> alike, in any language. Language-specific practices live on their own page
> ([Python](python.md)); deployable components additionally follow the
> [component standard](component-standard.md).

Conventions every repository shares, so tooling, CI, and contributor workflow
are the same everywhere.

## Distribution tier is explicit

A repo is **either** a library **or** a deployable component — decide and be
consistent. The tier determines which standards apply and how the package is
distributed.

| Tier | What it is | Ships as | How consumers/operators get it |
|---|---|---|---|
| **Library** | Imported by other packages; no runnable service | Source in its git repository | Depend on it from git — no package index |
| **Deployable component** | Ships a runnable service | Container image | Run the container, or install from a checkout |

(The one exception is the deployment system itself — see the
[bootstrap tier](deployment-system.md).) Packaging specifics per language:
[Python](python.md).

### No package index — consume libraries from git

**The stack does not publish to any package index (no PyPI, no npm, etc.).** It
is a single, first-party set of repositories; publishing and index accounts add
release machinery no one asked for. First-party libraries are consumed **directly
from their git repositories**, pinned by revision, using the language's native
git-dependency support — for Python, uv's `[tool.uv.sources]`:

```toml
[tool.uv.sources]
robotsix-config = { git = "https://github.com/damien-robotsix/robotsix-config.git", rev = "main" }
```

Repos therefore carry **no publish/release workflow** (no `pypi-publish`,
release-please, or index token). A library that later needs genuine public
distribution can add publishing back deliberately — but that is the exception,
not the default.

## Language practices

- **[Python](python.md)** — uv, hatchling, `requires-python` policy, console
  scripts, lint/type/security gates, test layout, pre-commit hooks.

New languages get their own page here before the first repo lands.

## Repo hygiene

- **Changelog.** Maintain `CHANGELOG.md` in [Keep a Changelog](https://keepachangelog.com)
  form under an `## 0.0.0 (unreleased)` heading; every PR adds an entry (CI
  enforces it).
- **Module registration.** Every file is registered in `docs/modules.yaml`
  under exactly one module; a drift check fails CI on unregistered or stale
  paths. New modules start by adding an entry there.
- **Truthful docs.** README / AGENT.md describe what the code actually does;
  don't let removed commands, renamed paths, or old version claims linger.
- **Point at the standards.** Every repo's `README.md` and `AGENT.md` link to
  [`robotsix-standards`](https://github.com/damien-robotsix/robotsix-standards)
  so contributors find the shared conventions from any repo.
- **License.** MIT, as a `LICENSE` file at the repo root.

## CI and security gates

Prefer the fleet's shared reusable workflows; pin every third-party action to a
commit SHA (with a `# vX.Y.Z` comment). The standard gate set:

- **Lint & types:** the language page's linters and type checker, as blocking
  gates ([Python](python.md): ruff, mypy strict, deptry).
- **Tests & coverage:** the test suite with a coverage floor enforced in CI
  (the fleet floor is **80%**).
- **Docs:** a strict docs build (`mkdocs build --strict`) when the repo
  publishes a docs site.
- **Security:** CodeQL (SAST), secret scanning + push protection, a dependency
  CVE audit, and `dependency-review` on PRs (`fail-on-severity: high`).
- **Container image:** repos that ship an image also scan it in CI — see
  [Docker build & release](docker-standard.md).

> **Dependency-review needs the Dependency graph enabled.** The
> `dependency-review` action errors with *"Dependency review is not supported on
> this repository"* until the repo's **Dependency graph** is turned on (enable
> Dependabot alerts / automated security fixes, which turn it on). Enable it once
> per repo, or the gate can never go green. It also only supports
> `pull_request` events — skip it on pushes (`if: github.event_name ==
> 'pull_request'`) or it fails every push to main.
