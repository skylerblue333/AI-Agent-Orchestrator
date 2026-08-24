from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from orchestrator import AgentSpec, Orchestrator, WorkflowError, prefix_handler


class RunRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=8000)


async def research(value: str) -> str:
    return await prefix_handler("research", value)


async def synthesize(value: str) -> str:
    return await prefix_handler("synthesis", value)


async def review(value: str) -> str:
    return await prefix_handler("review", value)


def build_orchestrator() -> Orchestrator:
    timeout = float(os.getenv("AGENT_TIMEOUT_SECONDS", "10"))
    agents = (
        AgentSpec("research", "Research stage", "research", timeout),
        AgentSpec("synthesis", "Synthesis stage", "synthesize", timeout),
        AgentSpec("review", "Review stage", "review", timeout),
    )
    return Orchestrator(
        agents,
        {"research": research, "synthesize": synthesize, "review": review},
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.orchestrator = build_orchestrator()
    yield


app = FastAPI(title="Sky Agent Orchestrator", version="0.1.0", lifespan=lifespan)


@app.get("/healthz")
async def healthz() -> dict[str, str]:
    return {"status": "healthy", "service": "sky-agent-orchestrator"}


@app.get("/readyz")
async def readyz() -> dict[str, object]:
    orchestrator: Orchestrator = app.state.orchestrator
    return {"status": "ready", "agents": len(orchestrator.agents)}


@app.post("/api/v1/workflows/run")
async def run_workflow(request: RunRequest) -> dict[str, object]:
    orchestrator: Orchestrator = app.state.orchestrator
    try:
        result = await orchestrator.run_workflow(request.objective)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except WorkflowError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return result.to_dict()
