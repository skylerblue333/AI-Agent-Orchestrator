# Sky Agent Orchestrator

A small, deterministic Python orchestration library and CLI for running a bounded sequence of injected asynchronous agent handlers.

**Status: engineering beta.** The repository implements workflow sequencing, validation, per-agent timeouts, structured results, tests, CI, dependency auditing and a non-root container. It does **not** include an LLM provider, autonomous planning, durable state, distributed execution, multi-tenancy, secrets management, production deployment or claims of enterprise/GA readiness.

## Why this exists

The original repository contained a three-step simulated-agent demo. The product branch preserves that concept while replacing the fixed sleep-based simulation with a reusable orchestration primitive whose handlers are explicitly supplied by the caller. This keeps provider choice and credentials outside the core engine.

## Core behavior

- 1–32 ordered agents per workflow.
- Unique agent names and validated roles/timeouts.
- Objectives limited to 10,000 characters.
- Per-agent execution timeout bounded to 300 seconds.
- Empty handler output is rejected instead of silently propagated.
- Deterministic step history and JSON serialization.
- No dynamic code evaluation or arbitrary plugin loading.

## Run

```bash
python -m pip install -r requirements.txt
python orchestrator.py "Analyze the release risks"
```

The included CLI uses deterministic prefix handlers as a smoke-test/demo. Real integrations should construct `Agent` objects with application-owned async handlers.

## Library example

```python
import asyncio
from orchestrator import Agent, Orchestrator

async def summarize(value: str) -> str:
    return f"summary: {value}"

workflow = Orchestrator([Agent("summary", "summarizer", summarize)])
result = asyncio.run(workflow.run_workflow("review this change"))
print(result.output)
```

## Verification

```bash
python -m compileall -q orchestrator.py tests
ruff check orchestrator.py tests
python -m pytest -q
pip-audit -r requirements.txt
docker build -t sky-agent-orchestrator .
docker run --rm --entrypoint id sky-agent-orchestrator -u
```

GitHub Actions enforces those gates plus a JSON CLI smoke test. The container runs as UID 10001.

## SKYCOIN4444 integration boundary

Use this package as an orchestration primitive behind HopeAI or other ecosystem services by injecting handlers that call those services through their documented APIs. Do not copy provider credentials or entire service implementations into this repository.

## Security boundaries

The engine treats objectives and handler outputs as untrusted strings. It does not execute them as code. Provider-specific prompt-injection defenses, authorization, rate limiting, tenant isolation, secrets storage and network policy belong at the integration layer and are not claimed here. See `SECURITY.md`.

## Versioning

The product branch is pre-1.0 engineering beta. See `CHANGELOG.md` for productization changes.
