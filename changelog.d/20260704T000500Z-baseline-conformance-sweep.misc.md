Baseline self-conformance sweep: standard pre-commit set (docs-repo
subset), shared baseline-check and dependabot-auto-merge callers, docs
deploy via the shared python-docs workflow (stale gh-deploy justification
removed), and a towncrier-ignored `.gitkeep` so `changelog.d/` survives
releases that consume every fragment.
