# Shared config shapes

> **Scope: every deployable component that carries one of the six
> cross-cutting config blocks defined here.** This page defines the
> canonical shape of each block so that every component models the same
> concept the same way. Per-component migration onto these shapes is
> tracked separately. See the [config standard](config-standard.md) for
> how config is modeled, loaded, and persisted, and
> [config ownership](config-ownership.md) for the deploy-plane vs
> component-owned boundary.

A fleet-wide settings audit (~480 settings across six config-owning
components) found the same config concepts duplicated under inconsistent
names and shapes: Langfuse credentials in four components, LLM backend
selection in six, logging toggles in three, HTTP bind addresses in three,
data directories in four, and GitHub App credentials in two. Each
component reinvents the field names, types, and nesting — so a config
consumer (the chat UI, cost-monitor, the deploy system) must know
per-component quirks instead of one contract.

This page defines the **six canonical shared config shapes**. Every
component that needs one of these blocks MUST use the shape defined here.
The shapes are pydantic v2 models (or fragments thereof) that a component
embeds in its own top-level config model. Field names, types, nesting,
and secret conventions are fixed — a component MAY add its own
component-specific fields alongside these blocks, but the shared blocks
themselves are not extended, renamed, or flattened.

## 1. Langfuse block

One `langfuse` block per component. Never per-account, never per-user.

```python
from pydantic import BaseModel, SecretStr


class LangfuseProject(BaseModel):
    """A single Langfuse project the component connects to."""

    project_id: str
    public_key: SecretStr
    secret_key: SecretStr


class LangfuseConfig(BaseModel):
    """Langfuse observability connection."""

    host: str = "https://cloud.langfuse.com"
    projects: dict[str, LangfuseProject] = {}
```

**Fields**

| Field | Type | Required | Description |
|---|---|---|---|
| `host` | `str` | No (default: cloud URL) | Langfuse server base URL. |
| `projects` | `dict[str, LangfuseProject]` | No | Named projects. Each key is a logical name the component uses to select a project; the value carries the Langfuse project id and its keypair. |

| Field (per project) | Type | Required | Description |
|---|---|---|---|
| `project_id` | `str` | Yes | Langfuse project identifier. |
| `public_key` | `SecretStr` | Yes | Langfuse public key. |
| `secret_key` | `SecretStr` | Yes | Langfuse secret key. |

**Failure prevented:** four components each define their own Langfuse
env-var names (`LANGFUSE_PUBLIC_KEY`, `langfuse.host`,
`analyst.langfuse_*`, per-account repetition in mail). An operator
rotating a Langfuse key must find and update every variant; missing one
silently breaks observability for that component.

**Migration note:** components currently using UPPERCASE `LANGFUSE_*`
environment variables MUST migrate to this block in `config.json` per
the [config standard](config-standard.md) one-file rule. The env-var
names are retired.

## 2. LLM backend and model selection

One `llm_backend` block for the LLM connection, plus a single canonical
`model_level` enum for high-level model selection.

```python
from enum import Enum

from pydantic import BaseModel, SecretStr


class ModelLevel(str, Enum):
    """Canonical model tiers. Components map these to concrete models."""

    level1 = "level1"
    level2 = "level2"
    level3 = "level3"


class LlmBackendConfig(BaseModel):
    """LLM provider connection details."""

    provider: str = "openai"
    endpoint_url: str = ""
    model: str = ""
    api_key: SecretStr = SecretStr("")
```

**Fields**

| Field | Type | Required | Description |
|---|---|---|---|
| `provider` | `str` | No (default: `"openai"`) | LLM provider identifier (e.g. `openai`, `anthropic`, `ollama`). |
| `endpoint_url` | `str` | No (default: empty) | Provider API base URL. Empty means the provider's default. |
| `model` | `str` | No (default: empty) | Concrete model identifier (e.g. `gpt-4o`, `claude-sonnet-4-20250514`). Empty means the component's default. |
| `api_key` | `SecretStr` | No | Provider API key. |

**`ModelLevel` enum**

The enum is defined **once** in the shared config shapes (or the shared
config library). Every component that offers tier-based model selection
imports this enum — it does not redefine its own copy. The enum has three
tiers; components map them to concrete models in their own runtime code.

**Failure prevented:** six components carry incompatible model-selection
mechanisms (`model_level` with six differently-scoped copies, `provider`/`model_id`
in invest, `global_model`/`trace_model` in cost-monitor, `llm_provider_model`
in mail, `enrichment_llm_*` in file-hub). An operator switching the fleet's
default model must update six different config shapes. One enum and one
backend block eliminate the drift.

**Ban on env-var indirection for keys:** the `api_key` field holds the
actual secret value as a `SecretStr`. Components MUST NOT introduce an
`api_key_env` field (or similar) that names an environment variable
containing the key — that violates the [config standard](config-standard.md)
one-file rule. The key lives in `config.json`, period.

## 3. Logging

Shared `log_level` and `log_format` fields. These are top-level fields on
the component's config model (not nested in a sub-block) because every
component carries them and nesting adds no value.

```python
from enum import Enum

from pydantic import Field


class LogLevel(str, Enum):
    """Canonical log levels."""

    debug = "debug"
    info = "info"
    warning = "warning"
    error = "error"
    critical = "critical"


class LogFormat(str, Enum):
    """Canonical log output formats."""

    json = "json"
    text = "text"
```

**Fields** (top-level on the component config model)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `log_level` | `LogLevel` | No | `info` | Minimum log severity. |
| `log_format` | `LogFormat` | No | `json` | Output format. `json` for structured JSON lines (per the [logging standard](logging.md)); `text` for human-readable dev output. |

**Failure prevented:** chat uses `log_json_format: bool`, invest uses
`debug: bool`, and other components use `LOG_LEVEL` env vars — three
incompatible ways to express the same two-axis setting. An operator
debugging a production issue must guess which toggle to flip per
component.

**Retired variants:** `log_json_format` (bool), `debug` (bool),
`LOG_LEVEL` env var. Components MUST migrate to the two-field shape
above.

## 4. HTTP host and port

One `server` block for the component's HTTP bind address.

```python
from pydantic import BaseModel


class ServerConfig(BaseModel):
    """HTTP server bind address."""

    host: str = "0.0.0.0"
    port: int = 8000
```

**Fields**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `host` | `str` | No | `"0.0.0.0"` | Bind address. |
| `port` | `int` | No | `8000` | Bind port. |

**Failure prevented:** mill uses `api_host`/`api_port`/`api_url`, chat
uses `server_host`/`server_port`, invest uses bare `host`/`port`. An
operator changing the port must know the per-component field name.
Derived fields like `api_url` are dropped — the URL is constructed from
`host` and `port` at runtime.

**Retired fields:** `api_host`, `api_port`, `api_url` (mill),
`server_host`, `server_port` (chat). Components MUST migrate to the
`server.host`/`server.port` block.

## 5. Storage / data directory

One `data_dir` field. Database paths, persistence paths, and other
storage locations are derived from it at runtime.

```python
from pathlib import Path

from pydantic import Field

# Top-level field on the component config model:
data_dir: Path = Field(
    default=Path("data"),
    description="Root directory for all persistent component data. "
    "Database files, caches, and other storage are derived from this path.",
)
```

**Field** (top-level on the component config model)

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `data_dir` | `Path` | No | `data` | Root directory for persistent data. All derived paths (database, cache, uploads) are subdirectories of this path. |

**Failure prevented:** four components define `database_url`,
`local_storage_path`, `persist_path`, and `data_dir` as independent
absolute paths. An operator relocating storage must update N fields per
component and keep them consistent. One root `data_dir` with derived
sub-paths makes relocation a single-field change.

**Retired fields:** `database_url`, `local_storage_path`, `persist_path`
(when they are absolute paths that could be derived from `data_dir`).
Components that need a genuinely external database connection (e.g. a
remote PostgreSQL URL) MAY keep that as a separate field — `data_dir` is
for local filesystem storage only.

## 6. GitHub App credentials

One `github_app` block for components that interact with GitHub as an
app.

```python
from pydantic import BaseModel, SecretStr


class GitHubAppConfig(BaseModel):
    """GitHub App authentication."""

    app_id: str = ""
    installation_id: str = ""
    private_key: SecretStr = SecretStr("")
    org: str = ""
```

**Fields**

| Field | Type | Required | Default | Description |
|---|---|---|---|---|
| `app_id` | `str` | No | empty | GitHub App ID. |
| `installation_id` | `str` | No | empty | GitHub App installation ID. |
| `private_key` | `SecretStr` | No | empty | GitHub App private key (PEM). |
| `org` | `str` | No | empty | GitHub organization the app is installed on. |

**Failure prevented:** mill uses `github_app_id`, `github_app_key`,
`github_installation_id`, `github_org` as flat top-level fields; chat
uses `direct_repo.app_id`, `direct_repo.private_key`, and a separate
`github_org`. An operator provisioning a new GitHub App must update two
different config shapes with different nesting and naming. One block
eliminates the mapping.

**Retired fields:** `github_app_id`, `github_app_key`,
`github_installation_id`, `github_org` (mill flat fields),
`direct_repo.*` (chat nested fields). Components MUST migrate to the
`github_app` block.

## Cross-cutting rules

### Secrets are `SecretStr`, never env-var indirection

Every secret field across all six shapes uses `pydantic.SecretStr`. No
component introduces an `_env` suffix field that names an environment
variable — the secret value lives in `config.json` per the
[config standard](config-standard.md) one-file rule.

*Failure prevented:* an `api_key_env` field means the actual secret is
stored in a second location (an env file, a Docker Compose `environment`
block), violating the one-file invariant and making secret rotation
a two-place operation.

### Shapes are embedded, not imported from a shared library

Each component defines these models in its own codebase (or imports them
from `robotsix-config` once the shared library publishes them). The
canonical definition lives in this standards page; the shared library is
the implementation vehicle, not the source of truth. If the standard and
the library ever diverge, the standard wins.

*Failure prevented:* if the shapes lived only in a library, a component
that pins an older library version would silently use a stale shape — and
the deploy UI would render fields the component no longer recognises.

### One block per component, never per-account or per-user

The Langfuse block, LLM backend block, and GitHub App block are
component-level config. They are defined once in the component's
`config.json`, not repeated per account, per user, or per workspace.

*Failure prevented:* mail currently repeats Langfuse credentials per
email account. Rotating a key means updating N copies; missing one
breaks observability for that account silently.
