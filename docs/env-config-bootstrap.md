# Env/config variables — resolve once in a config bootstrap

> **Scope: every repository that reads configuration from environment
> variables**, in any language (PHP `getenv`/`$_ENV`, Python
> `os.getenv`/`os.environ`, Go `os.Getenv`, JavaScript `process.env`, shell).
> Libraries take their configuration through their own API (constructor
> arguments or an explicit config object); this convention governs the env
> reads that remain at an application's edge. It complements the
> [config standard](config-standard.md), which models runtime config as one
> typed JSON file — the env-var reads that survive (e.g. the file's location,
> a history cap) still resolve through a single bootstrap.

## Why this exists

Environment variables are configuration. Like any configuration, they must
have **one authoritative resolution point** so `where is this variable read?`
has exactly one answer. When `getenv()`/`os.getenv()`/`process.env` calls are
scattered across consumer files, each with its own inline default, the same
variable drifts — different defaults in different call sites, and an override
set in the environment silently missed where one call site hard-codes a
value.

Mature ecosystems converge on the same shape:

- **Laravel (PHP)** loads `.env` via `vlucas/phpdotenv` at bootstrap, then
  `config/*.php` files read each value once via `env('VAR', default)`; all
  other code uses the `config()` facade. Calling `env()` outside config files
  is explicitly discouraged.
- **Symfony (PHP)** resolves `%env(VAR)%` at container compile in
  `config/packages/*.yaml`; consumer code never calls `getenv()`, it injects
  the resolved parameter through DI.
- **WordPress (PHP)** defines constants
  (`define('DB_NAME', getenv('DB_NAME'))`) in a single `wp-config.php` — one
  central location.

The fleet already follows this pattern: `robotsix-config` reads
`ROBOTSIX_CONFIG_FILE` exactly once in `resolve_config_path()`, and
`ROBOTSIX_CONFIG_MAX_VERSIONS` exactly once in the history store loader, both
with documented in-repo defaults. This page codifies the same principle for
every repo that reads environment variables for configuration.

## The rule

### 1. A single config bootstrap resolves every env/config variable

Every environment-variable read for configuration lives in **one dedicated
bootstrap** — a `config.php`, a `settings.py` loaded at startup, a `config`
package in Go, a JS config module imported once, a shell bootstrap script.
That file is the **only** place in the repo where `getenv()`/`os.environ`/
`os.Getenv`/`process.env` is called for configuration, and it is where every
variable's **documented default** lives.

*Failure prevented:* a person deploying or debugging asks *"where is
`SURVEY_RATE_LIMIT_DIR` set / what happens if I unset it?"* and has to grep
the whole tree for `getenv(` call sites — each with a different fallback — to
reconstruct an answer that should be visible in one file.

### 2. Consumers read from the bootstrap — never call `getenv()` inline

All other code gets its value from the bootstrap: the `config()` facade in
Laravel, an injected resolved parameter in Symfony, an imported module
constant, a constructor argument handed the resolved value. No consumer file
calls `getenv()`/`os.getenv()`/`process.env` ad hoc with its own default.

*Failure prevented:* a new contributor adds a feature in
`www/42/admin/survey_migration.php` and writes
`getenv('SURVEY_DB_PATH') ?: 'surveys.db'` — a default that drifts from the
one in the bootstrap. The system now has two answers for "where does
`SURVEY_DB_PATH` live and what does it default to."

### 3. Defaults are documented once, in the bootstrap

The bootstrap declares, for each variable, its name, its default, and (where
it matters) its meaning — so the read is self-documenting and the default is
unambiguous across every consumer.

*Failure prevented:* two files read the same variable with different inline
defaults (`SURVEY_DB_PATH ?: 'surveys.db'` in one, a different path in
another), and an operator who sets the variable expect both to change finds
one site ignores it.

The `ROBOTSIX_*` namespace is **machine-checked**: the
`check-config-single-source` pre-commit hook (published via
`.pre-commit-hooks.yaml`, consumed as a remote hook like `check-secret-str`)
fails on any `ROBOTSIX_*` env read that is not one of the two allowed vars —
`ROBOTSIX_CONFIG_FILE` (read once in `resolve_config_path()`) and
`ROBOTSIX_CONFIG_MAX_VERSIONS` (read once in the history store loader) — and
on either allowed var resolved at more than one call site. General per-repo
config env vars (e.g. `SURVEY_*`) have no hook and remain self-policing; the
single-bootstrap rule above is their guardrail.

## Canonical anti-pattern (verified fleet example)

`robotsix-website` reads the `SURVEY_*` variables ad hoc in four distinct
places, each with its own fallback:

| File | Read |
|---|---|
| `www/42/admin/survey_data_base.php:30` | `getenv($this->envVar()) ?: dirname(__DIR__).'/data'` |
| `www/42/admin/survey_migration.php:26` | `getenv('SURVEY_DB_PATH') ?: ...'surveys.db'` |
| `www/42/inc/error_log.php:22` | `getenv('SURVEY_LOG_FILE')` |
| `www/42/survey_submit.php:70` | `getenv('SURVEY_RATE_LIMIT_DIR') ?: sys_get_temp_dir().'/survey_rate_limit'` |

That scattering is the failure this convention prevents. The same four
variables should instead be resolved once, with defaults, in a
`config.php`-style bootstrap (e.g. a `SURVEY_*` block of
`define()`d constants or a small config module), and every consumer should
read the resolved value from there.

## Precedent

- [Laravel](https://laravel.com/docs/configuration) — `env()` only in config
  files, `config()` everywhere else; `config:cache` relies on values being
  resolved once.
- [Symfony](https://symfony.com/doc/current/configuration/env_var_processors)
  — `%env(VAR)%` resolved at container compile; consumer code injects the
  parameter.
- [WordPress](https://developer.wordpress.org/advanced-administration/security/hardening/)
  — `wp-config.php` centralizes all `define(..., getenv(...))` reads.
- **robotsix-config** — `ROBOTSIX_CONFIG_FILE` and
  `ROBOTSIX_CONFIG_MAX_VERSIONS` each read once, at a single accessor, with
  documented defaults (see the [config standard](config-standard.md)).
