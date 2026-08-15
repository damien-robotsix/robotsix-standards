# Config self-healing

> **Scope: deployable components** that use the shared configuration library
> ([`robotsix-config`](https://github.com/damien-robotsix/robotsix-config)).
> This page defines the runtime behaviour that the library must implement so
> removed config fields do not crashloop a service — the companion library
> ticket covers the implementation.

**When a config key is removed from the model, the persisted config file on
the live volume still carries the stale block. A strict `extra=forbid` model
rejects unknown keys at startup and the container crashloops — a production
outage.** The shared config library MUST strip unrecognized keys on load (with
a warning) and rewrite the config file so the warning does not recur. Every
component that uses the library inherits this behaviour — no per-service
reimplementation.

## The rule

### 1. Load-path leniency

When loading already-persisted config (`load_config`), unrecognized keys
(keys present in the JSON file but absent from the pydantic model) MUST be
stripped silently from the validated model — rather than raising
`ValidationError` and crashing startup.

The library MUST emit a **WARNING**-level log record naming each stripped
key and its top-level path, so the operator knows stale keys were removed.
Example:

```text
WARNING: robotsix_config.loader: stripping unrecognized config key
'legal_guardrails' (not present in model 'InvestConfig') — config will be
rewritten to remove it
```

### 2. Write-path strictness

Incoming runtime writes (`PUT /config`, `dump_config`, or any code path that
persists a config model to disk) MUST still **reject unknown keys**. Only
the load path is lenient — the write path remains strict (`extra=forbid`)
so operators never persist a key the model does not declare.

This ensures the operator cannot accidentally save a typo'd or unsupported
field through the deploy UI, while a service that already carries stale keys
from a previous deploy boots cleanly.

### 3. Self-heal on load

After stripping unrecognized keys, the library MUST rewrite the on-disk
config file so the removed keys are gone permanently. The rewrite uses the
same `dump_config` path (atomic write, `0600` permissions) and happens
immediately after load — before the application's first config read.

The self-heal is **idempotent**: a second load finds a clean file, emits no
warning, and performs no rewrite. The warning appears at most once per
deploy — the first boot after a feature removal strips the stale keys, and
subsequent boots are silent.

### 4. Library responsibility — not per-service

This behaviour MUST be implemented in the **shared config library**
([`robotsix-config`](https://github.com/damien-robotsix/robotsix-config)),
in the `load_config` function that every component calls. Individual
services MUST NOT reimplement stripping, self-healing, or lenient-load
logic — the library is the single point of enforcement.

The companion library ticket defines the implementation: a lenient parse
pass (pydantic `model_validate` with `extra="ignore"` vs. strict
`extra="forbid"`), a key-diff to identify what was stripped, the warning
log record, and the immediate `dump_config` rewrite.

### 5. Feature-removal checklist

When a PR removes a config-backed feature from a service, the author MUST
also migrate or remove the corresponding persisted config in the same change.
A removal that leaves the model and the live volume out of sync is
incomplete — the stale block on disk is exactly what crashloops the service
on the next deploy (the `legal_guardrails` incident). Every removal PR MUST:

1. **Update the config loader to tolerate/strip the removed key.** The load
   path must not fail validation on the stale key. Either the shared
   library's strip-on-load behaviour is shipped and active in the target
   image, or the removal PR updates the component's load path so the removed
   key is tolerated and stripped rather than rejected.
2. **Clear the stored config on deploy (if applicable).** If the removed key
   is present in the persisted config on the live volume and the library
   self-heal is not active, the PR ships the deploy-side cleanup — a startup
   config-rewrite, a deploy hook, or an explicit removal step — so the stale
   block is removed rather than merely tolerated forever.
3. **Verify the service starts without error.** Before the removal is
   complete, the author MUST confirm the new image boots cleanly against a
   volume that still carries the stale key — the load path strips the key
   (warning once), the config is rewritten, and the service reaches ready.

A removal MUST **never** assume that stored config is already clean — the
config file on the live volume is the state that the library's lenient-load
or an explicit migration must handle.

## Why

Two crashloop incidents have already occurred in the fleet (robotsix-invest
after the legal-guardrails removal, and earlier cases during the YAML→JSON
cutover). Each followed the same pattern: a feature was removed, its config
field disappeared from the model, the persisted config file on the volume
still carried the old key, and the strict model rejected it at startup —
crashloop with no human in the loop.

The self-healing library rule prevents this class of outage entirely: the
service boots, warns, strips the stale key, and keeps running. The operator
sees the warning in logs and can verify the config file was cleaned, but the
service never goes down because of a removed config field.

## Failure modes this prevents

- **Crashloop on feature removal.** Without lenient-load, removing a config
  field in code causes every deployed instance to crash at startup because
  the persisted config file still carries the old key. The self-heal
  prevents this entirely.
- **Warning-storm on every boot.** Without the self-heal rewrite, lenient
  load alone would emit the same warning on every boot indefinitely,
  training operators to ignore it. The one-shot rewrite keeps the signal
  clean.
- **Per-service drift.** Without the library rule, each service would
  reimplement (or forget) lenient-load differently — some crash, some strip,
  some silently ignore. One library implementation keeps behaviour uniform
  across the fleet.

## Relationship to other standards

- **[Config standard](config-standard.md)** — defines the "one pydantic model,
  one JSON file" rule that this page extends. The self-healing behaviour is
  a property of `load_config` in the same shared library.
- **[Component standard](component-standard.md)** — the deploy modes and
  image lifecycle; the self-heal runs at startup in every mode identically.
- **[Deploy contract](deploy-contract.md)** — the config file lives on a
  mounted volume; the self-heal writes back to that volume on first boot
  after a feature removal.
