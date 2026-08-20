# ROS 2 practices

> **Scope: every ROS 2 repository.** These are the language-specific
> practices for ROS 2 packages; the language-agnostic rules (tiers, hygiene,
> CI philosophy) live in the [repo baseline](repo-baseline.md).

!!! note "Status: derived from robotsix-mill-ros2"

    The `robotsix-mill-ros2` repo predates this standards page; the
    conventions below are extracted from that repo's actual working
    practices. This page will expand as more ROS 2 repos land in the fleet
    and as existing patterns are documented.

## What kind of repo?

ROS 2 repos in the fleet follow a **workspace-skeleton** model: the repo
is an orchestrator that declares downstream package repos, not a bag of
ROS 2 packages itself. Actual ROS 2 packages (with `package.xml` and
`CMakeLists.txt`) live in the downstream repos listed in the workspace
manifest.

The workspace repo is a **deployable component** — it ships a container
image (via the [Docker build & release](docker-standard.md) pattern) and follows
the [component standard](component-standard.md) for its deploy modes.

## Supported ROS 2 distros

- **Rolling is the default.** The devcontainer Dockerfile uses
  `ros:rolling-ros-base` and CI gates against Rolling.
- **The Dockerfile is parametric** — `ROS_DISTRO` is a build arg (default
  `rolling`), so any distro with an official `ros:$DISTRO-ros-base` image
  (Humble, Jazzy, Lyrical) works. Switch the build arg to change distros.
- **No multi-distro CI matrix yet.** The single CI job gates against one
  distro at a time. A matrix across distros is expected once the fleet has
  multiple ROS 2 repos that need it.

## Workspace layout

```text
├── repos.yaml              ← vcs2l manifest: downstream package repos
├── src/                    ← git-ignored; populated by `vcs import`
├── .devcontainer/
│   ├── Dockerfile          ← FROM ros:$ROS_DISTRO-ros-base
│   └── devcontainer.json
├── justfile                ← local lint/validate orchestrator
├── scripts/
│   └── update_workspace.sh ← vcs import + rosdep wrapper
├── .robotsix-mill/
│   └── config.yaml         ← mill config: languages, test gate
└── .github/
    └── workflows/
        └── ci.yaml         ← CI gate (justfile recipes)
```

**Key rules:**

- **`src/` is always git-ignored.** Source packages come from downstream
  repos via `vcs import < repos.yaml` — they are never committed into the
  workspace repo.
- **The workspace manifest (`repos.yaml`) is the single source of truth**
  for which packages belong in the workspace. It uses the
  [vcstool](https://github.com/dirk-thomas/vcstool) format.
- **Branch refs in `repos.yaml` are acceptable** — unlike first-party git
  dependencies in Python repos (which are pinned to commit SHAs per the
  [repo baseline](repo-baseline.md#pin-to-a-commit-sha-not-a-branch)),
  workspace manifests track development branches so `vcs import` pulls the
  latest. CI gates against the branch head, so drift is visible and
  intentional.

## Devcontainer

Every ROS 2 workspace repo ships a `.devcontainer/` so the development
environment is reproducible:

```dockerfile
FROM ros:$ROS_DISTRO-ros-base

# System dependencies for building and tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential cmake git ccache \
    python3-pip python3-vcstool python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*

# Non-root user with passwordless sudo
RUN useradd -m -s /bin/bash ros && echo "ros ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers
USER ros

# Source ROS setup on login
RUN echo "source /opt/ros/$ROS_DISTRO/setup.bash" >> ~/.bashrc
```

**`devcontainer.json` conventions:**

- `remoteUser: ros` — run as the non-root user.
- Workspace mounted at `/home/ws`.
- ROS discovery scoped to localhost:

  ```json
  "containerEnv": {
    "ROS_DOMAIN_ID": "42",
    "ROS_AUTOMATIC_DISCOVERY_RANGE": "LOCALHOST",
    "CCACHE_DIR": "/home/ws/.ccache"
  }
  ```

- `--net=host` and `--ipc=host` for DDS networking.
- A named `ccache` volume mounted at `${CCACHE_DIR}` so the compiler
  cache persists across devcontainer rebuilds:

  ```json
  "mounts": [
    "source=ros2-ccache,target=${containerEnv:CCACHE_DIR},type=volume"
  ]
  ```

  **Why a named volume:** bind-mounting a host directory works locally
  but breaks in remote (GitHub Codespaces) and CI-hosted devcontainer
  environments. A named Docker volume works everywhere and is cheap
  to recreate — the cache is an optimisation, not precious state.
- `postCreateCommand` runs `vcs import`, `rosdep update`, and
  `rosdep install` so the workspace is ready on first open.

## Build & test

The standard build lifecycle:

```bash
# 1. Pull in downstream packages
vcs import src < repos.yaml

# 2. Resolve system dependencies
rosdep update
rosdep install --from-paths src --ignore-src -y

# 3. Build the workspace (with ccache if configured)
colcon build --symlink-install \
    --cmake-args -DCMAKE_C_COMPILER_LAUNCHER=ccache \
                -DCMAKE_CXX_COMPILER_LAUNCHER=ccache

# 4. Run tests
colcon test

# 5. (optional) Show test results
colcon test-result --verbose
```

### ccache integration

**ccache is required for all C++ ROS 2 workspace devcontainers.**
Without it, `colcon build` recompiles every translation unit from scratch
on each devcontainer rebuild — easily 5–20 minutes of wall-clock time
for a mid-size workspace.

**Setup (three pieces, all in `.devcontainer/`):**

1. **Install ccache** in the Dockerfile (`apt-get install ccache`).
2. **Set `CCACHE_DIR`** in `devcontainer.json` `containerEnv` to
   `/home/ws/.ccache` (or a similar workspace-relative path).
3. **Mount a named volume** at that path so the cache survives rebuilds.

**colcon CMake args** wire ccache into the build as shown above.
If a downstream package uses a non-CMake build system (e.g. pure-Python
packages), the cmake args are ignored — ccache only accelerates C/C++
compilation, which is the dominant cost in ROS 2 workspaces.

### colcon build lifecycle

The full colcon build lifecycle for development:

| Step | Command | When |
|------|---------|------|
| Full build | `colcon build --symlink-install` | First checkout, after `rosdep install` |
| Incremental build | `colcon build --symlink-install --packages-select <pkg>` | After editing a single package |
| Clean rebuild | `rm -rf build/ install/ && colcon build --symlink-install` | After dependency changes or stale artifacts |
| Test all | `colcon test` | After any build |
| Test one package | `colcon test --packages-select <pkg>` | During development on that package |

- **`colcon build --symlink-install`** is the default — Python packages
  are symlinked so edits take effect without re-building.
- **`rosdep` resolves system-level dependencies** (apt packages) declared
  in each downstream package's `package.xml`.
- **`vcs import` is the standard tool** for cloning downstream repos from
  the workspace manifest.

## CI expectations

ROS 2 workspace repos gate on a single `ci.yaml` workflow. The gate
covers linting and validation — build and test run in the devcontainer
during development; CI is the hygiene gate.

**Lint recipes** (run via `just check`, the justfile default):

| Recipe | What it checks |
|---|---|
| `lint-yaml` | `yamllint --strict` on all YAML files |
| `lint-shell` | `shellcheck` on workspace scripts |
| `lint-spelling` | `codespell` across the repo |
| `lint-markdown` | `markdownlint` on docs |
| `validate-manifest` | `vcs validate --input repos.yaml` |
| `lint-actions` | `actionlint` on `.github/workflows/` |
| `lint-security` | `zizmor` on CI workflows |

Additionally, the fleet-wide `pre-commit` hooks (see the
[Python practices](python.md#pre-commit-hooks) — the set is the same for all
repos) apply — the CI job runs `pre-commit run --all-files --verbose`.

**No build or test in CI yet.** The current CI gate is lint/validate only;
`colcon build` and `colcon test` run locally in the devcontainer. This
will change as the ROS 2 fleet grows and a shared build-and-test workflow
is factored out (the pattern: one CI job per distro in a matrix, gate on
build + test passing across all supported distros).

## Code style & linting

- **Python packages** (inside downstream ROS 2 packages) follow the fleet
  [Python practices](python.md): ruff, mypy, deptry, bandit.
- **C++ packages** follow ROS 2 community conventions: `ament_lint` for
  linting (`ament_cpplint`, `ament_clang_format`), `clang-tidy` for static
  analysis. Specific tool configs live in each downstream repo.
- **Shell** (workspace scripts): `shellcheck` via the justfile.
- **YAML**: `yamllint --strict` — no warnings tolerated.
- **Markdown**: `markdownlint` on all `.md` files.
- **Spelling**: `codespell` — catches typos across the entire repo.
- **Workflows**: `actionlint` for CI YAML correctness; `zizmor` for
  workflow security (excessive permissions, injection vectors).

## Interface design

ROS 2 interface files (`.msg`, `.srv`, `.action`) live in the downstream
package repos, not in the workspace skeleton. Standard ROS 2 layout
applies:

```text
<package>/
├── msg/        ← .msg files (message definitions)
├── srv/        ← .srv files (service definitions)
├── action/     ← .action files (action definitions)
├── CMakeLists.txt   ← registers the interface files for codegen
└── package.xml      ← declares build dependencies on rosidl
```

**Rules (provisional — to be hardened as more ROS 2 repos land):**

- **Interfaces are versioned with their package** — no separate
  interface-only package unless the interface is genuinely shared across
  multiple consumers from different repos.
- **`rosidl_default_generators`** in `package.xml` for message generation;
  C++ packages additionally depend on `rosidl_default_runtime`.
- **Interface files use the standard ROS 2 field types** — no custom
  primitive wrappers.

These rules will be refined once the fleet has more than one ROS 2
package repo to observe consistency across.
