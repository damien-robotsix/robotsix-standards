# Default config location

> **Scope: deployable components only.** See the
> [component standard](component-standard.md).

Every deployable component ships a **default config file** at a standardized
in-repo location. The deployment system reads this file exactly once — when the
repo is first registered — to seed the deploy-side config. After seeding, the
deploy-side config is the operator's to edit; the shipped default is never
consulted again.

## The rule

### 1. Canonical location: `config/config.json` at the repo root

The shipped default config lives at **`config/config.json`** at the repository
root — the same path the component reads at runtime per the
[config standard](config-standard.md) (located by `ROBOTSIX_CONFIG_FILE`, which
defaults to that path). The file is a valid instance of the component's config
model: every required field has a value, every optional field carries its
sensible default, and no field is left dangling.

*Failure prevented:* central-deploy registers a new repo and starts the
component with an empty deploy-side config. The component fails at startup
with a validation error (e.g. `'agents': [] should be non-empty`) because the
deploy-side config shadows the repo's shipped default — but the deploy-side
config was never seeded.

### 2. Relationship to the `robotsix.deploy.config-target` compose label

The `robotsix.deploy.config-target` label on the primary service in
`deploy/docker-compose.yml` declares **where the config file is injected
inside the container** at runtime (e.g. `/home/app/config/config.json`).
That label is part of the [deploy contract](deploy-contract.md) and is
consumed by central-deploy at every config save — the deployment system
writes the deploy-side config into the mounted volume at that path before
the container starts.

The shipped default at `config/config.json` is the **seed value** for that
deploy-side config. On first registration of a repo, central-deploy copies
the shipped default into the deploy-side config store. The
`config-target` label is the *target*; the shipped default is the *source*.
They are separate concerns:

| Concern | Where defined | Consumed by |
|---|---|---|
| Where the config goes inside the container | `robotsix.deploy.config-target` label in `deploy/docker-compose.yml` | central-deploy (every config save) |
| The seed value for the deploy-side config | `config/config.json` at the repo root | central-deploy (once, on first registration) |

*Failure prevented:* a repo ships a valid default config but central-deploy
never reads it because the convention for *where* to find it was never
standardized — the deployment system hard-codes a path guess that differs
from what the repo actually ships.

### 3. Validation expectation

When a repo ships a `config/config.schema.json` alongside the default config
(per the [config standard](config-standard.md) §2 — the typed schema emitted
from the pydantic model), the shipped `config/config.json` **MUST validate**
against that schema. A repo that ships a default config that fails its own
schema is shipping a broken seed.

The validation is enforced by a **CI check** in every deployable repo:
regenerate the schema from the model, then validate `config/config.json`
against it. The check catches:

- A field added to the model whose default config entry is missing or mistyped.
- A field removed from the model whose default config entry is stale.
- An enum value renamed in the model but not updated in the default config.

*Failure prevented:* an operator onboards a repo whose shipped default config
is out of sync with its own schema. central-deploy seeds the deploy-side
config with the broken default; the component fails at startup, and the
operator has no indication that the repo itself is the root cause — the error
looks like a deploy misconfiguration.

### 4. Consumer guidance

**central-deploy** (and any future tooling that manages deploy-side config) is
the primary consumer of this convention. The rules for the consumer:

- **Seed once.** On first registration of a repo, resolve the shipped default
  from `config/config.json` at the repo root and use it to populate the
  deploy-side config store. This is the only time the shipped default is read.
- **Never overwrite.** Once the deploy-side config exists — whether seeded or
  operator-edited — the shipped default is never consulted again. An operator
  edit to the deploy-side config (through the Configure UI or the config API)
  is the source of truth; re-seeding would silently revert operator work.
- **Detect absence.** If a repo ships no `config/config.json`, central-deploy
  seeds an empty config — the component starts with its model defaults (per the
  config standard's field-default-fill rule). This is a valid state for
  components whose defaults are production-safe; it is not an error.
- **Detect invalidity.** If the shipped default fails validation against
  `config/config.schema.json` (when one exists), central-deploy MUST reject the
  onboarding with a clear error naming the offending field — not silently seed
  a broken config.

The central-deploy ticket that implements this seeding behavior is
`20260724T132650Z-seed-deploy-side-config-from-repo-defaul-b159` on the
robotsix-central-deploy board. That ticket is the primary consumer of this
standard; this standard exists so the location convention is defined here
rather than hard-coded ad-hoc inside central-deploy.

*Failure prevented:* central-deploy implements seeding but resolves the
shipped default from a hard-coded path that differs from what one repo
actually ships — the convention was never written down, so each consumer
guesses.

## Why not bake the default into the image?

The config file is a volume mount, not a baked-in image layer, because the
deployment system must be able to write operator edits into it at runtime.
If the default were baked into the image at `/home/app/config/config.json`,
the volume mount would shadow it on first deploy — and because the volume
is empty, the component would start with no config at all. The shipped
default at the repo root exists precisely to prevent that empty-volume
window: central-deploy reads it, writes it into the volume, and the
component starts with a valid config from the first deploy.
