Added a **Module taxonomy scope** standard: `docs/modules.yaml` inventories
product code, not the repository's own build, lint, packaging and release
scaffolding. Rule 6 of the changelog standard, which previously *required*
registering every towncrier fragment in the taxonomy, is inverted to forbid it —
its own rationale had conceded the requirement was "a recurring friction point"
while documenting the workaround rather than removing the cause.
