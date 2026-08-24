# Sky Agent Orchestrator

**Status: engineering beta**

A focused Python service for coordinating a bounded sequence of explicitly registered asynchronous agent handlers. The service preserves this repository's original multi-stage orchestration idea while replacing simulated "LLM call" behavior and placeholder CI with deterministic, testable execution semantics.

## Implemented

- bounded task intake with UUID task IDs
- explicit `plan`, `execute`, and `review` stages
- per-agent timeout enforcement and fail-closed error handling
- task capacity and concurrency limits
- health, readiness, task-status, and metrics endpoints
- deterministic step ordering and output validation
- tests for orchestration order, timeouts, capacity, validation, and API behavior
- Ruff, pytest, dependency-audit, Docker-build, and non-root-image CI gates

The built-in stage handlers are deterministic examples. The orchestration core accepts injected async handlers so integrations can connect approved model, search, workflow, or business-service clients without giving this repository arbitrary-code execution.

## API

Run locally:

```bash
python -m pip install -r requirements-dev.txt
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

Health and readiness:

```bash
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

Create a task:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/tasks \
  -H 'content-type: application/json' \
  -d '{"objective":"summarize approved portfolio evidence","stages":["plan","execute","review"]}'
```

Read a task using the returned UUID:

```bash
curl http://127.0.0.1:8000/api/v1/tasks/<task-id>
```

Metrics:

```bash
curl http://127.0.0.1:8000/metrics
```

## Configuration

| Variable | Default | Bound |
| --- | ---: | --- |
| `MAX_TASKS` | `1000` | 1–100000 |
| `MAX_CONCURRENT_TASKS` | `8` | 1–128 |
| `AGENT_TIMEOUT_SECONDS` | `10` | 0.05–120 |
| `LOG_LEVEL` | `INFO` | Python logging level |

Invalid numeric configuration fails during startup.

## Verification

```bash
python -m compileall -q orchestrator.py src tests
ruff check orchestrator.py src tests
python -m pytest -q
pip-audit -r requirements.txt
docker build -t sky-orchestrator .
docker run --rm --entrypoint=id sky-orchestrator -u
```

The container is configured to run as UID/GID `10001`.

## Architecture

`src/main.py` owns the HTTP/task boundary and bounded in-memory task state. `orchestrator.py` owns handler registration, stage ordering, timeout enforcement, and result validation. Integrations should supply explicit async handlers to the core rather than allowing user-provided code, module names, shell commands, or unrestricted URLs.

## SKYCOIN4444 integration

This service can sit behind Sky Gateway as an orchestration boundary for HopeAI or other ecosystem workflows. Integration should use the HTTP API or the Python orchestration contract instead of copying the implementation into a flagship repository.

## Current limitations

This is not a production deployment or a general autonomous-agent platform. Task state is in-memory and is lost on restart. There is no durable queue, distributed worker fleet, external model connector, tenant isolation, authentication/authorization layer, billing, human-approval system, persistence, HA, or exactly-once guarantee. Deployment, TLS, ingress, backups, and production monitoring are not verified here.

See `SECURITY.md` for security boundaries and `CHANGELOG.md` for productization history.
