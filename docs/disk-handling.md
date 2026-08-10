# Multi-disk data handling

> **Scope: deployable components and the deployment system.**
> Cross-refs: [component standard](component-standard.md),
> [deploy contract](deploy-contract.md),
> [Docker build & release](docker-standard.md),
> [deployment system](deployment-system.md).

The server has multiple physical disks (e.g. a smaller root disk and a larger
data disk mounted at `/data2`). Without a fleet-wide standard for how a
component's persistent data volume is placed onto — and later moved between —
disks, every component handles storage ad-hoc. The deploy dashboard had to be
reworked to report per-disk usage, a deploy-time disk selector was added to
central-deploy (PR #729), and some components shipped with no persistent volume
at all. This standard defines the contract so every component handles
multi-disk storage the same way.

## No default disk in the component repo

A component declares its data volume in its deploy spec **without** hard-coding
a host disk or mount path. The component repo's job is to state *what data it
needs persisted*, not *where on the host that data lives*.

**Rule:** The component's `deploy/docker-compose.yml` declares a **named data
volume**. The volume name describes the data (e.g. `file-hub-data`,
`chat-sessions`), never the physical disk. No `device`, `driver_opts`, or
host-path mount belongs in the component repo's compose file — those are
placement decisions the deployment system owns.

```yaml
# In the component repo — correct (disk-agnostic):
volumes:
  file-hub-data:

services:
  file-hub:
    volumes:
      - file-hub-data:/data
```

**Failure mode prevented.** When a component hard-codes a host path (e.g.
`/data2/file-hub`) it ties the deployment to one disk layout, breaks on every
host that differs, and forces operators to edit the repo source to move data.
Named volumes decouple the component from the host's physical layout and let
the deployment system choose the backing disk at deploy time.

Components that today ship with **no persistent volume at all** (e.g. the
file-hub before its persistent-volume work) violate this rule: a service whose
data disappears on restart is not deployable. Every deployable component that
holds state — files, databases, session data — must declare at least one named
data volume.

## Target disk chosen at deploy time

The physical disk a component's data volume lands on is selected
**case-by-case when the component is added or deployed** in central-deploy.
This is the single source of truth for volume placement — no other mechanism
(compose `driver_opts`, host-wide Docker daemon config, operator shell scripts)
overrides it.

**Rule:** The deploy-time disk selector (shipped in [central-deploy
PR #729](https://github.com/damien-robotsix/robotsix-central-deploy/pull/729))
is the **sole mechanism** for choosing which physical disk backs a component's
data volume. The operator sees available disks and their free space, picks one,
and the deployment system creates the named volume on that disk. The component
repo never participates in this decision.

**Failure mode prevented.** Before the disk selector existed, operators had to
know the host's disk layout, guess which disk had space, and manually place
volumes — a process that varied per component and per host. Centralizing the
choice in the deploy UI makes it auditable (the dashboard records which disk
every volume lives on), repeatable (no host-specific knowledge needed), and
safe (free space is visible before the choice is made).

## Volumes are relocatable between disks

An operator must be able to move an existing component's data volume from one
physical disk to another later, **without data loss**. A disk that fills up, a
hardware replacement, or a planned rebalancing must not require deleting and
re-creating the volume.

**Rule:** The deployment system provides a **relocate workflow** that:

1. stops the component (the component's data must be quiescent);
2. copies the volume's data to the target disk (preserving ownership, permissions,
   and timestamps — `rsync -a` semantics);
3. re-points the named volume to the new physical location;
4. restarts the component against the relocated volume.

The component itself is **never aware** of the relocation — it continues to
read and write the same mount path (e.g. `/data`), and the named volume name
does not change. Only the backing disk changes, and the deployment system is
the sole actor that touches the volume at rest.

**Failure mode prevented.** Without a defined relocate workflow, a full disk
forces the operator to either (a) manually `rsync` data and hand-edit Docker
volume metadata — a risky, unrepeatable process — or (b) discard the data and
start fresh. A standard relocate guarantee makes disk space management a
routine operation instead of an incident.

> **Note:** The relocate capability is a central-deploy implementation
> concern. If the deploy plane cannot yet relocate a live volume, file a
> follow-on central-deploy ticket to add it. The standard defines the
> *guarantee* the fleet relies on; the implementation closes the gap.

## Disk usage reported per physical device

Operators need to see free space **per physical disk** before choosing where
to place a new volume or whether to relocate an existing one. An aggregate
number that double-counts bind-mounts or merges all disks into one figure is
misleading and unsafe.

**Rule:** The deployment system's disk usage panel reports **one row per
physical block device**, showing total space, used space, and free space for
each. Named volumes are attributed to the disk they physically reside on — the
reporting follows the filesystem, not Docker's volume abstraction.

**Failure mode prevented.** Aggregate disk usage (e.g. summing `df` across all
mount points without deduplication) hides which disk is actually full, causing
operators to pick the wrong target for a new volume or fail to notice that a
single disk is nearing capacity. Per-device reporting makes the storage layout
legible so placement decisions are informed.

## Reference implementations

- **[central-deploy PR #729](https://github.com/damien-robotsix/robotsix-central-deploy/pull/729)** —
  the deploy-time disk selector and per-disk usage display that implement the
  "target disk chosen at deploy time" and "per-disk observability" rules.
- **file-hub persistent data volume** — the first component to ship a
  disk-agnostic named data volume (no default disk, no host path) following
  this standard; demonstrates the "no default disk in the component repo" rule
  in a real deployable component.
