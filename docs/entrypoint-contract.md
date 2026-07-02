# Entrypoint contract

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).

A shared container `entrypoint.sh` pattern, so every component image behaves the
same at startup regardless of which deploy mode launched it.

## Behavior

The entrypoint must:

1. **Locate config the standard way.** Read `ROBOTSIX_CONFIG_FILE` (default
   `config/config.yaml`) — the same variable the app uses (see the
   [config standard](config-standard.md)).
2. **Validate config presence for commands that need it**, and **skip that
   check** for commands that don't (`detect`, `--help`, `--version`, other
   bootstrap subcommands). A service that can generate its own config must be
   runnable before a config exists.
3. **Enforce `0600` on the config file** if it holds secrets (the app/library's
   `write_config_file` does this when it writes; the entrypoint tightens an
   externally-mounted file defensively).
4. **`exec` the application** as the final step, so signals (SIGTERM from
   `docker stop`) reach the Python process directly — never run the app as a
   child of the shell.
5. **Handle SIGTERM for long-running loops.** A `--watch`/daemon subcommand
   should stop cleanly on SIGTERM (log a stop line, drain if mid-cycle, exit 0),
   not be hard-killed. `exec` covers signal delivery; the app implements the
   handler.

## Anti-patterns to avoid

- **Dead `envsubst` templating.** Don't template config with `envsubst` unless
  `gettext-base` is actually installed in the runtime image stage — otherwise
  `command -v envsubst` fails and the block silently does nothing (a real bug
  found in the stack). There is nothing to template anyway: per the
  [config standard](config-standard.md) the one config file is the only source
  of values (no env overlay), so delete any `envsubst` block.
- **Running the app without `exec`.** `docker stop` then can't deliver SIGTERM
  to Python; the container is SIGKILLed after the grace period with no clean
  shutdown.
- **Requiring config for `--help`/`detect`.** Blocks the bootstrap path a fresh
  operator needs.

## Skeleton

```sh
#!/bin/sh
set -eu

CONFIG_FILE="${ROBOTSIX_CONFIG_FILE:-config/config.yaml}"

case "${1:-}" in
  detect|--help|-h|--version|"")
    exec robotsix-<service> "$@" ;;   # bootstrap/no-config commands
esac

if [ ! -f "$CONFIG_FILE" ]; then
  echo "config file not found: $CONFIG_FILE" >&2
  exit 1
fi
# Tighten perms defensively if the file carries secrets.
chmod 0600 "$CONFIG_FILE" 2>/dev/null || true

exec robotsix-<service> "$@"          # exec so SIGTERM reaches the app
```
