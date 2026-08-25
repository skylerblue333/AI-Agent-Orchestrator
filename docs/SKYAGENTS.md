# SkyAgents — Slot #90 / Lane 12

SkyAgents is an engineering-beta orchestration library for executing an explicit ordered list of caller-supplied asynchronous handlers.

## Supported boundary

- Validates bounded agent IDs, task IDs, payloads, task counts, and per-task timeouts.
- Requires all handlers to be registered by the caller.
- Rejects duplicate task IDs and unknown agents.
- Executes tasks deterministically in submitted order and returns structured results.
- Fails on timeout, missing handler, malformed input, or empty handler output.

## SKYCOIN4444 integration contract

A SKYCOIN4444 component may register trusted local adapters and submit `AgentTask` objects to `AgentRegistry.execute`. The caller remains responsible for authentication, authorization, prompt/input policy, provider credentials, persistence, observability, retries, and any external side effects.

## Truth and security boundaries

This module does not discover agents, plan autonomously, call an LLM, connect to an external model provider, persist memory, run distributed workers, sandbox arbitrary code, or claim production deployment. Registered handlers execute with the permissions of the hosting process, so callers must not register untrusted code.

## Verification

CI compiles and lints both orchestration modules, runs deterministic pytest coverage, audits Python dependencies, smoke-tests the existing CLI, and verifies the existing non-root container image.
