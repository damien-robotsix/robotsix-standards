# JavaScript practices (frontend)

> **Scope: every repository that ships browser JavaScript.** These are the
> language-specific practices; the language-agnostic rules live in the
> [repo baseline](repo-baseline.md). Conventions here were proven out in
> robotsix-board; other frontends align to them.

## Scope of the language

Frontend JavaScript in the stack is **vanilla JS served as static assets from
the Python package** (`src/<pkg>/static/`) — no bundler, no build step, no
TypeScript, no framework. A build pipeline is machinery nobody asked for;
like PyPI publishing, one can be added back deliberately if a frontend
genuinely outgrows static files — that is the exception, not the default.

## Manifest & lockfile

- `package.json` **and** `package-lock.json` are committed; the lockfile is
  the source of truth for reproducible installs.
- **Never hand-edit `package-lock.json`** — it is generated from
  `package.json` by `npm install`.
- When dependency lines change (`dependencies`, `devDependencies`,
  `peerDependencies`), regenerate the lockfile (`npm install` or
  `npm install --package-lock-only`) and commit it **in the same change** —
  CI uses `npm ci`, which fails on a stale lockfile, by design.
- Metadata-only `package.json` edits (a `scripts` entry, config sections)
  don't require lockfile regeneration.

## Tests

- **vitest** with `@vitest/coverage-v8`, run in CI (`vitest run --coverage`).
- The `thresholds` in `vitest.config.mjs` are the **same fleet-wide floor as
  Python: 80** (see [Tests](python.md#tests)) — one number, never lowered to
  make a PR pass; add tests instead. The floor moves only fleet-wide.
- **Every module-level function is attached to an explicit export surface**
  (e.g. a public `window.<pkg>*` assignment or a `…Internals` object for
  testable helpers), so every function is unit-testable. *Rationale: a
  function missing from the export surfaces was the one function (of 29)
  that couldn't be unit-tested directly (robotsix-board, ticket
  `20260618T142122Z`).*

## Style

- **No presentational styles from JS.** Never set colors, fonts, margins,
  layout, or initial visibility via `element.style.*` / `cssText` — apply a
  class name and define the appearance in the stylesheet. Behavioral
  visibility toggles on events (`el.style.display = 'none'` to show/hide)
  and `el.id` selector hooks are permitted. *Rationale: inline styles
  override the stylesheet, making class-based theming impossible; recurring
  incident class in robotsix-board.*
- **camelCase** for all function names.

## Lint & hooks

- `eslint` (JS) and `stylelint` (CSS), as pre-commit hooks alongside the
  [standard Python set](python.md#pre-commit-hooks).

## Dependency updates

Repos with a `package.json` add the **`npm`** ecosystem to `dependabot.yml`
(see [automated dependency updates](repo-baseline.md#automated-dependency-updates)).

## Vulnerability scanning

**A blocking `npm audit` CI gate is intentionally NOT part of this
standard.** Frontend CVE detection is already mandated through Dependabot
(above), which detects vulnerable dependencies and opens fix PRs — that is
the sanctioned mechanism.

- **`npm audit` MUST NOT be wired as a required/blocking CI check.**
  npm advisories can fire on transitive dependencies outside the team's
  control; a newly-published advisory turns CI red on unrelated PRs until
  someone bumps the dep or raises the audit level threshold. This
  "flaky-red" tax blocks unrelated work for low marginal safety: the
  vulnerability is already visible to Dependabot, and the fix PR is the
  correct channel.
- **Contrast with Python:** the [Python standard](python.md) mandates a
  blocking `pip-audit` gate paired with a commented suppression allow-list
  for CVEs that have no fix. The frontend standard deliberately relies on
  Dependabot instead of a blocking audit gate.
- If a team wants PR-time visibility, `npm audit` may be run as an
  **advisory-only / non-blocking** job (e.g. `npm audit || true`), never
  as a gate.
