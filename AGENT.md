# Agent guide

This repo **is** the [robotsix stack standards](https://github.com/damien-robotsix/robotsix-standards)
— the docs under `docs/` are the product. It is a documentation repo (no
runnable service, no published package); the repo-baseline rules apply where
relevant.

Build the docs: `uv run --group docs mkdocs build --strict` (CI gates on it).

## Rules

**Rule:** Standards pages state rules and their failure modes; they never
embed GitHub-workflow YAML. Caller templates live in the
[robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows)
README.
**Rationale:** embedded YAML is a copy that drifts from the workflow it calls;
the template must version with the workflow (2026-07 standards review).

**Rule:** Before editing a claim about fleet behavior (uids, tags, workflows,
Dockerfile patterns, compose shapes), verify it against the actual repos under
`~/projects/Robotsix/` — and when the fleet has already solved the problem,
document the fleet's proven pattern rather than inventing one.
**Rationale:** contradictions between pages and reality were the main defect
class in the 2026-07 review (a Dockerfile example that never built, a curl
healthcheck the image can't run, three different claude-mount targets).

**Rule:** Every rule added to a standard states the failure it prevents.
**Rationale:** rules without stated failure modes read as bureaucracy and get
half-followed; the stated failure is also what lets a future edit decide
whether the rule still applies.

**Rule:** The deploy contract's canonical copy lives in central-deploy
(`docs/DEPLOY_CONTRACT.md`); `docs/deploy-contract.md` here is a pointer, not
a copy — never inline contract content into this repo.
**Rationale:** an earlier copy kept here drifted from the implementation and
had to be removed.

**Rule:** When editing or creating deployment-engine guidance (especially
`docs/deployment-system.md`), the deployment engine is a **generic control
plane** — it must not carry per-service or per-repo definitions in its source
code. Service definitions belong in the persisted component config store
(onboarding API), a `virtual_components` config key, a `langfuse_projects`
config dict, or per-component boolean flags. If a proposed rule change would
require hard-coding a service name, project alias, or hostname in engine code,
reject it — the pattern is declarative data, never engine code.
**Rationale:** hard-coding service definitions in engine code makes the engine
a bottleneck (2026-07 standards review).
