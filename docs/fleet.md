# The fleet

Every robotsix repo, what it is, and where its docs live. (Every repo
publishes a docs site — see [Docs](python.md#docs).) Add a row when a repo is
created; remove it when one is archived.

## Shared libraries & tooling (every-repo tier)

| Repo | What it is | Docs |
|---|---|---|
| [robotsix-standards](https://github.com/damien-robotsix/robotsix-standards) | This site — the fleet's shared conventions. | [site](https://damien-robotsix.github.io/robotsix-standards/) |
| [robotsix-config](https://github.com/damien-robotsix/robotsix-config) | The shared configuration library implementing the [config standard](config-standard.md). | [repo](https://github.com/damien-robotsix/robotsix-config) |
| [robotsix-llmio](https://github.com/damien-robotsix/robotsix-llmio) | LLM provider abstraction — capability levels, cost tracking, tracing. | [repo](https://github.com/damien-robotsix/robotsix-llmio) |
| [robotsix-modules](https://github.com/damien-robotsix/robotsix-modules) | `docs/modules.yaml` tooling — module map, drift gate. | [repo](https://github.com/damien-robotsix/robotsix-modules) |
| [robotsix-github-workflows](https://github.com/damien-robotsix/robotsix-github-workflows) | The shared reusable workflows (the fleet's CI gates). | [repo](https://github.com/damien-robotsix/robotsix-github-workflows) |
| [robotsix-board](https://github.com/damien-robotsix/robotsix-board) | Ticket-board UI library. | [repo](https://github.com/damien-robotsix/robotsix-board) |

## Deployable components

| Repo | What it is | Docs |
|---|---|---|
| [robotsix-central-deploy](https://github.com/damien-robotsix/robotsix-central-deploy) | The deployment system ([bootstrap tier](deployment-system.md)). | [repo](https://github.com/damien-robotsix/robotsix-central-deploy) |
| [robotsix-mill](https://github.com/damien-robotsix/robotsix-mill) | The agent-driven ticket pipeline (draft → implement → review → deliver). | [repo](https://github.com/damien-robotsix/robotsix-mill) |
| [robotsix-chat](https://github.com/damien-robotsix/robotsix-chat) | Browser + SSE chat server exposing an LLM agent to human users. | [repo](https://github.com/damien-robotsix/robotsix-chat) |
| [robotsix-auto-mail](https://github.com/damien-robotsix/robotsix-auto-mail) | Mail automation service. | [repo](https://github.com/damien-robotsix/robotsix-auto-mail) |
| [robotsix-calendar-agent](https://github.com/damien-robotsix/robotsix-calendar-agent) | Calendar agent service. | [repo](https://github.com/damien-robotsix/robotsix-calendar-agent) |
| [robotsix-cost-monitor](https://github.com/damien-robotsix/robotsix-cost-monitor) | Cost dashboard. | [repo](https://github.com/damien-robotsix/robotsix-cost-monitor) |
| [robotsix-mill-ros2](https://github.com/damien-robotsix/robotsix-mill-ros2) | ROS 2 companion to the mill. | [repo](https://github.com/damien-robotsix/robotsix-mill-ros2) |
