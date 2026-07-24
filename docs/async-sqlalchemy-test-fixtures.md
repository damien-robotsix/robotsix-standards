# Async SQLAlchemy test fixtures

> **Scope: every Python repository using async SQLAlchemy.** This convention
> applies fleet-wide so every test suite gets clean database isolation without
> dropping/recreating tables, and without ad-hoc module-level global-state
> management.

## Why this exists

Every fleet repo that uses async SQLAlchemy eventually needs a test fixture that
provides a database session for route-level code — and every repo invents its
own.  Some use an autouse fixture that resets module-level globals; others spin
up the engine inside a per-test helper and call `init_db()` manually in each
test function.  These approaches work but they share two failure modes:

- **Per-test table recreation is slow** — creating and dropping the full schema
  for every test function adds seconds per test, and the penalty compounds as
  the schema grows.
- **Module-level global state is fragile** — an autouse fixture that patches
  globals couples test ordering to import-time state, and any mis-handled async
  lifecycle (missed `await`, forgotten `close()`) leaks connections and state
  across tests.

The three-layer pattern below — session-scoped engine, function-scoped
connection, function-scoped session — gives every test its own isolated
transaction that is **rolled back on teardown**, so tables are created once and
data never leaks between tests.  No global state, no per-test `init_db()`
boilerplate, no ad-hoc `_reset_db_globals`.

The pattern is drawn from the SQLAlchemy 2.x documentation
([Joining a Session into an External Transaction](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html#joining-a-session-into-an-external-transaction-such-as-for-test-suites))
and the Litestar SQLAlchemy template.

## The three layers

Place these three fixtures in a `tests/conftest.py` at the package root so
every test module under `tests/` inherits them.

### 1. Session-scoped engine

Creates the database tables **once** for the entire test session.

```python
import pytest
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.fixture(scope="session")
def anyio_backend():
    return "asyncio"


@pytest.fixture(scope="session")
async def engine():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()
```

- `anyio_backend` is required — pytest-asyncio alone cannot drive async
  SQLAlchemy; the `anyio` plugin is the fleet-wide async test runner.
- `sqlite+aiosqlite:///:memory:` gives a fast, isolated in-process database.
  Each test session gets its own fresh in-memory database, so there is no
  risk of cross-session contamination even when tests run in parallel.
- `conn.run_sync(Base.metadata.create_all)` calls the synchronous DDL path
  inside the async connection so the ORM metadata is created without a
  blocking thread-switch.
- `engine.dispose()` on teardown releases the connection pool cleanly.

### 2. Function-scoped connection with outer transaction

Wraps every test function in an **outer transaction** that is never committed.

```python
@pytest.fixture
async def connection(engine):
    async with engine.connect() as conn:
        async with conn.begin():
            yield conn
        # rollback happens when the context manager exits
```

- `conn.begin()` starts an explicit transaction at the connection level.
- The yield hands the connection — with an active transaction — to the test.
- When the test function returns, the `async with conn.begin():` block exits
  and the transaction is **rolled back**, discarding every row that was
  inserted, updated, or deleted during the test.
- No table drops, no `TRUNCATE`, no `DELETE` — just a single rollback.

### 3. Function-scoped async session bound to that transaction

Creates a SQLAlchemy `AsyncSession` that participates in the connection's
outer transaction via savepoints.

```python
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def db_session(connection):
    session = AsyncSession(
        bind=connection,
        expire_on_commit=False,
        join_transaction_mode="create_savepoint",
    )
    try:
        yield session
    finally:
        await session.close()
```

- **`bind=connection`** wires the session to the function-scoped connection
  with its outer transaction.
- **`expire_on_commit=False`** prevents SQLAlchemy from expiring all loaded
  objects after a `session.commit()`, which avoids lazy-load surprises inside
  test assertions.
- **`join_transaction_mode="create_savepoint"`** is the key behaviour: when
  route code (or any code under test) calls `session.commit()`, SQLAlchemy
  converts it into a `SAVEPOINT`/`RELEASE` pair *inside* the outer
  transaction.  The outer transaction itself is never committed — it is always
  rolled back on teardown, so the test's writes are always discarded.

## Usage in tests

Inject `db_session` into any async test function that needs a database:

```python
async def test_create_widget(db_session):
    repo = WidgetRepository(db_session)
    widget = await repo.create(name="gizmo")
    assert widget.id is not None
    # The row is present inside this test's transaction ...
```

```python
async def test_widgets_are_isolated(db_session):
    count = await db_session.scalar(select(func.count(Widget.id)))
    assert count == 0  # ... but invisible to the next test
```

## Overriding fixtures for a specific test

Sometimes a test needs a fixture override — for example, to seed data before
the test runs.  The standard approach is to define a module-local helper that
calls the parent fixture:

```python
@pytest.fixture
async def seeded_session(db_session):
    db_session.add_all([Widget(name="a"), Widget(name="b")])
    await db_session.flush()
    return db_session
```

This keeps the three-layer isolation intact — the seed data is inside the same
outer transaction and will be rolled back at teardown.

## What to avoid

- **Do not drop or recreate tables per test.**  The session-scoped engine
  creates the schema once; the function-scoped rollback handles isolation.
- **Do not use module-level globals** to hold the engine or session factory.
  Pytest fixtures already manage lifecycle at the correct scope.
- **Do not call `await db_session.commit()` in test code** and expect the data
  to persist to the next test — it is a savepoint release inside a
  rollback-only outer transaction.
- **Do not use `expire_on_commit=True` (the default).**  It causes
  `DetachedInstanceError` when asserting on ORM objects after the code under
  test has called `commit()`.
