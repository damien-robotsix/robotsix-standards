# FastAPI Pydantic field descriptions

> **Scope: deployable components that expose a FastAPI application.** A
> component whose only HTTP surface is the mandatory `/health` endpoint (see
> the [component standard](component-standard.md)) does not need this. This
> applies *in addition to* the [repo baseline](repo-baseline.md) and
> [component standard](component-standard.md).

Every FastAPI service in the fleet generates an OpenAPI schema (`/openapi.json`)
consumed by operators, downstream tools, and the Swagger UI. Pydantic v2 does
**not** parse inline trailing `#` comments on field lines for JSON-schema
descriptions — those are plain Python comments, invisible to
`model_json_schema()`. Without explicit descriptions, the generated schema is
undocumented at the field level: every field shows only its Python name and
type annotation, forcing every consumer to guess at semantics.

**The rule: every field on a Pydantic `BaseModel` that reaches the API surface
must carry a description.**

## What is the API surface?

A model is on the API surface when it appears in any of these FastAPI
positions:

- A **response model** (`response_model=`, or the return-type annotation of a
  path operation).
- A **request body** (a parameter annotated with `Body(...)` whose type is a
  Pydantic model, or a model-type parameter without a `Body`/`Query`/`Header`
  annotation — FastAPI treats bare non-scalar types as bodies).
- A **`Query`**, **`Header`**, **`Cookie`**, or **`Path`** parameter whose
  type is a Pydantic model (or whose individual fields are extracted via
  `Query()`).
- Any model **nested** inside one of the above — descriptions propagate
  through the JSON schema, so nested model fields also reach `/openapi.json`.

Models used only for internal logic — database rows, internal DTOs, config
models — are exempt.

## How to describe fields

### Recommended: `Field(description=...)`

Colocate the description with the field definition using Pydantic's `Field`:

```python
from pydantic import BaseModel, Field


class CreateTicketRequest(BaseModel):
    title: str = Field(description="Short summary of the ticket")
    body: str = Field(description="Markdown body of the ticket")
    priority: int = Field(default=0, description="Lower is more urgent; 0 means unset")
```

`Field(description=...)` is immune to docstring-parsing edge cases and keeps
the description immediately next to the definition. This is the fleet's
convention — already in use in `robotsix-central-deploy` (`registry/models.py`,
`caretaker/models.py`, `lifecycle/schemas.py`).

### Acceptable alternative: Google-style `Attributes:` docstring

A Google-style docstring on the model class is an acceptable alternative:

```python
class CreateTicketRequest(BaseModel):
    """A request to create a new ticket.

    Attributes:
        title: Short summary of the ticket.
        body: Markdown body of the ticket.
        priority: Lower is more urgent; 0 means unset.
    """

    title: str
    body: str
    priority: int = 0
```

Pydantic v2 parses the `Attributes:` block and feeds each field's description
into the JSON schema. However, this approach has edge cases: the parser does
not recognise multi-line field descriptions that omit a blank line before the
next `field_name:`, and it cannot describe fields inherited from a parent
class. Prefer `Field(description=...)` for new code.

## Enforcement (optional but encouraged)

Add an automated check that warns or fails when an API-surface model field
has no description:

- A small AST walker that inspects `pydantic.BaseModel` subclasses in a
  repository, flags fields without `Field(description=...)` or a
  `Field(default=..., description=...)`, and cross-references the class
  against the application's route registration.
- When integrated into the shared `python-ci.yml` reusable workflow, it
  becomes a fleet-wide gate — every repo inherits the check at zero marginal
  cost.

This check is **optional** today; a repo that adds it signals that its API
surface is fully documented. The fleet convention is the requirement — the
automated gate is the enforcement.

## Cross-reference

- **[FastAPI test isolation](fastapi-test-isolation.md)** — the other
  fleet-wide FastAPI convention: mutable server state must be exposed
  through `Depends()` dependencies so tests can override via
  `app.dependency_overrides` rather than importing and mutating module-level
  globals.
