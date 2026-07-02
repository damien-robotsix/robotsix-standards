# Config standard

**One config schema per service, defined once, that resolves the same way in all
three deploy modes.** This is the core of the stack standard; the
[`robotsix-config`](https://github.com/damien-robotsix/robotsix-standards)
library implements it so services get it by subclassing one base model.

## The rule

### 1. One file, one schema, one locate variable

- Runtime config is a **single YAML file**, default path `config/config.yaml`
  (matching the central-deploy contract), located by **one** environment
  variable: **`ROBOTSIX_CONFIG_FILE`**. Per-service legacy names
  (`MAIL_CONFIG_PATH`, `MILL_CONFIG_FILE`) are **removed, not aliased** — the
  stack is pre-release, so a clean break is preferred over back-compat.
- The **same filename in every mode** — `config.yaml` in dev docker *and* under
  central-deploy. (No more `mail.local.yaml` in dev but `config.yaml` in
  deploy.)
- The schema is defined once, in **pydantic v2**. Pydantic is what lets the same
  model validate the file, emit the central-deploy template, and mask secrets —
  one definition, three uses. (Frozen dataclasses, as auto-mail uses today, are
  the outlier and should migrate.)

### 2. Fixed precedence (lowest -> highest)

```
built-in defaults  <  config.yaml  <  ROBOTSIX_ env overlay  <  explicit kwargs (CLI)
```

- **File is the base; env overlays it; the CLI wins.** This keeps the file as
  the human-readable source of truth while allowing container/operator env
  overrides — without the per-repo contradictions.
- Env overlay keys are **derived mechanically from the schema path** under a
  single prefix `ROBOTSIX_<SERVICE>_`, with `__` for nesting (e.g.
  `ROBOTSIX_MAIL_IMAP__HOST`). No hand-maintained per-variable lists. Verbatim
  third-party aliases (`OPENROUTER_API_KEY`, `LANGFUSE_*`) are the one allowed
  exception, declared in a shared list.

### 3. One secret convention

- A secret field is declared with **`pydantic.SecretStr`**. It is **masked on
  read** (`repr`/`str` show `**********`, never the value).
- In the generated template a secret is an **empty leaf** (`key: ""`) — this is
  already the central-deploy contract convention, so the deploy template *is*
  the schema template. The `SECRET` sentinel is retired.
- Any config file written with real secrets is created **`0600` in a `0700`
  directory**, enforced in shared loader code — not per-repo, not
  docstring-only. No real credentials committed anywhere, even gitignored.

## Using the library

```python
from pydantic import SecretStr
from pydantic_settings import SettingsConfigDict
from robotsix_config import RobotsixConfig, emit_deploy_template


class ImapConfig(RobotsixConfig):
    model_config = SettingsConfigDict(env_prefix="ROBOTSIX_MAIL_", env_nested_delimiter="__")
    host: str = "localhost"
    port: int = 993


class MailConfig(RobotsixConfig):
    model_config = SettingsConfigDict(
        env_prefix="ROBOTSIX_MAIL_", env_nested_delimiter="__", extra="ignore"
    )
    log_level: str = "info"
    password: SecretStr = SecretStr("")
    imap: ImapConfig = ImapConfig()


# Resolution: defaults < ROBOTSIX_CONFIG_FILE yaml < ROBOTSIX_MAIL_* env < kwargs
cfg = MailConfig()

# Persist merged config with 0600 perms (e.g. central-deploy writing the volume):
from robotsix_config import write_config_file
write_config_file("config/config.yaml", cfg.model_dump())

# Emit the central-deploy config/config.yaml template from the schema:
print(emit_deploy_template(MailConfig))
# log_level: info
# password: ''          <- secret slot
# imap:
#   host: localhost
#   port: 993
```

The library API:

| Symbol | Purpose |
|---|---|
| `RobotsixConfig` | Base `BaseSettings` with the fixed source ordering. |
| `resolve_config_path()` | The `ROBOTSIX_CONFIG_FILE`-or-default path. |
| `write_config_file(path, data)` | Write YAML `0600` in a `0700` dir. |
| `emit_deploy_template(model_cls)` | Generate the central-deploy config template. |
| `CONFIG_FILE_ENV`, `DEFAULT_CONFIG_PATH` | The standard var name and default. |

## Why this resolves the survey's key finding

Today the "same shape across three modes" property holds only for the two
YAML-based services, and even they use different schema tools, precedence, and
locate-variables. A shared model makes the property hold for the **whole stack
by construction** — the same class instance is what a `uv`-installed run, the
dev container, and central-deploy all read, and the drift check
(`check_config_sync`, currently a per-repo script in auto-mail) becomes a shared
CI helper.

## Rollout (incremental, clean cutover)

The stack is pre-release with no external users, so migrations are a **clean
cutover** — no deprecated aliases or compatibility shims.

1. Publish `robotsix-config` (`requires-python >=3.11` so the library tier can
   use it).
2. Migrate services one at a time: auto-mail (dataclasses -> pydantic,
   `config.yaml` filename in dev, `0600` enforcement), then mill (precedence
   already close), then central-deploy adopts `ROBOTSIX_CONFIG_FILE`. Old
   env-var names are dropped, not aliased.
3. Turn `check_config_sync` into the shared CI gate so drift can't reappear.

Each service migrates in one step — there's no dual-config transition to manage.
