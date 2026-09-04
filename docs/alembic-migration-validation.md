# Alembic migration validation in CI

> **Scope: every Python repository that manages its database schema with
> Alembic** (typically a FastAPI or other web-service backend deployed to
> production with a specific schema). Such a repo must validate its
> migrations in CI by executing them against a fresh test database — never
> by relying on `Base.metadata.create_all` alone.

## The rule

**Any repo that ships Alembic migrations must run a CI job that executes the
migrations against a fresh test database, on every push and pull request.** The
job must:

1. Create a fresh test database (in-memory SQLite for repos with no DB-specific
   feature requirements, or a Docker-backed Postgres/MySQL service otherwise).
2. Run `alembic upgrade head` to validate the forward migrations end-to-end.
3. Run `alembic downgrade base` (optional but recommended) to validate that the
   reverse migrations are also executable.
4. Fail the job if any migration step fails.

The test suite must not be the sole source of the schema. A repo whose tests
build the schema via `Base.metadata.create_all` must still run the migration
job, because `create_all` and `upgrade head` are not the same operation.

## Why

A repo that builds its test schema with `Base.metadata.create_all`
(SQLAlchemy's direct DDL path) and never runs Alembic in CI ships with several
silent defects:

- **Migration syntax and logic errors are never caught before deployment.**
  A migration that is valid SQLAlchemy metadata but malformed as an Alembic
  `op` sequence, or that depends on a state introduced by an earlier revision,
  only fails at deploy time — after the code is already in production.
- **`upgrade` and `downgrade` are never exercised.** Neither the forward nor
  the reverse path is executed anywhere, so a broken `downgrade` (or an
  `upgrade` that leaves the DB in a state the app cannot use) goes unnoticed
  until an operator runs `alembic` against a real database.
- **Production deployments can fail silently.** A migration issue surfaces as a
  deploy-time or first-request-time failure, often with an opaque stack trace
  and no signal that the schema, not the app code, is at fault.
- **The test schema diverges from the production schema.** `create_all` only
  creates tables that exist in the current ORM metadata; it does not apply
  migration *side effects* (backfills, data transforms, index changes,
  renames) or respect migration *ordering dependencies*. Tests can pass against
  a schema that production migrations never produce.

This pattern is standard in industry projects (Django, Rails, and FastAPI +
Alembic templates all validate migrations in CI) precisely because it turns a
deploy-time surprise into a fast, local CI failure.

## How to comply

The caller template for the migration-validation job lives in the
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
README, alongside the workflow it calls — that is the single source of truth.
**Do not inline the workflow YAML into this page.**

- A repo with a Docker-backed database service (Postgres/MySQL) should run the
  migration job against that service so DB-specific features are exercised.
- A repo with no DB-specific feature requirements may use an in-memory SQLite
  database. In-memory SQLite must be a *fresh, per-run* database so migrations
  run against a clean schema every time.
- The migration job is an auxiliary gate: it does not replace the lint /
  type-check / test sequence described in [Python CI workflow](python-ci-workflow.md),
  and the shared `python-ci.yml` workflow does not (by default) run migrations.
  Add the migration job alongside it.

### Example invocation (informative)

The rule above — not this snippet — is normative; the exact invocation is the
workflow template's job. In outline, the job runs the migrations against the
fresh database and fails the job on any error:

```text
uv run alembic -c alembic.ini upgrade head   # validate forward migrations
uv run alembic -c alembic.ini downgrade base # validate reverse migrations
```

## What this does not cover

- **Schema drift detection** between the ORM metadata and the migrated schema
  (`alembic check` / `autogenerate` diffs) is a separate concern and not
  required by this rule.
- **Running migrations against a live production database.** This rule is about
  validating migrations in CI on a throwaway database; production schema
  migration is a deploy-time concern covered by the
  [deploy contract](deploy-contract.md).

## Failure modes prevented

- **Deploy-time migration failure.** A migration error that would have failed
  `alembic upgrade head` is caught in CI instead of during a production deploy.
- **Un-tested reverse migrations.** A broken `downgrade` (which matters for
  rollbacks) is caught before it is ever needed.
- **Silent test/production schema divergence.** Tests no longer pass against a
  `create_all`-only schema that production migrations would never produce.
