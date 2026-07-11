# Entrypoint contract

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).

How a component's container starts. The rule is simple: **the console script
is PID 1.**

## The standard: no entrypoint script

The default — what most of the fleet ships — is a direct exec-form entrypoint
in the Dockerfile:

```dockerfile
ENTRYPOINT ["robotsix-<name>"]
```

Every duty an entrypoint script used to carry has a better home:

- **Signal delivery** — exec form makes the console script PID 1, so SIGTERM
  from `docker stop` reaches the Python process directly. A `--watch`/daemon
  subcommand stops cleanly on SIGTERM (log a stop line, drain if mid-cycle,
  exit 0) — the **app** implements the handler.
- **Config validation** — `robotsix_config.load_config` already fails fast
  with a clear `MissingConfigError`/`InvalidConfigError`; a shell pre-check
  duplicates it with a worse message. Bootstrap commands that must run before
  a config exists (`detect`, `--help`, `--version`) simply don't call
  `load_config` — the app knows which of its commands need config, whereas a
  shell-script allowlist of subcommand names rots the first time one is added.
- **Config file permissions** — enforced by whoever *writes* the file:
  `dump_config` writes `0600` in a `0700` directory, and central-deploy owns
  the config volume it writes into. Not a per-container `chmod`.

## The exception: genuine startup work

A component ships an `entrypoint.sh` only when the container must do real work
before the app can run that the app itself cannot do — the canonical example
is robotsix-mill's privilege drop: start as root to reconcile config/data
volume ownership (`chmod 600` secrets, `chown` to the runtime user) and raise
the fd ulimit, then `runuser` down to the app user. The older
socket-group-join pattern is the legacy direct-mount branch, which the deploy
contract forbids for app containers. If you are not sure you need one, you
don't.

Rules for such a script:

1. **`exec` the application as the final step** — never run the app as a child
   of the shell, or `docker stop` can't deliver SIGTERM and the container is
   SIGKILLed after the grace period with no clean shutdown.
2. **Never gate bootstrap commands on config** (`--help`, `detect`, …) — a
   fresh operator must be able to run them before any config exists.
3. **No config templating.** Don't template with `envsubst`: per the
   [config standard](config-standard.md) the one config file is the only
   source of values, so there is nothing to template — and `gettext-base`
   isn't in the runtime image anyway, so the block silently does nothing (a
   real bug found in the stack). Delete any `envsubst` block.
4. **Keep it short, and comment why it exists** — the script is an exception;
   the comment is its justification.
