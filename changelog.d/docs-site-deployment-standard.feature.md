Added a **Docs site deployment** standard covering the GitHub Pages contract for
repos that publish: the caller-permission triple the shared `python-docs.yml`
spine requires, the Pages source setting that must accompany it, and who owns
concurrency. A fleet audit found six different pins of that one workflow, four
caller-permission shapes, three Pages configurations, and three repos whose Docs
workflow had never once run — a permissions mismatch fails at startup with no
logs, no checks and nothing on the PR, so nothing surfaces it.
