from __future__ import annotations

import asyncio
import logging
import os
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from threading import Lock
from time import monotonic
from uuid import UUID, uuid4

from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from orchestrator import AgentSpec, Orchestrator, WorkflowError

SERVICE_NAME = "sky-agent-orchestrator"
MAX_TASKS = int(os.getenv("MAX_TASKS", "1000"))
MAX_CONCURRENT_TASKS = int(os.getenv("MAX_CONCURRENT_TASKS", "8"))
AGENT_TIMEOUT_SECONDS = float(os.getenv("AGENT_TIMEOUT_SECONDS", "10"))
if MAX_TASKS < 1 or MAX_TASKS > 100_000:
    raise RuntimeError("MAX_TASKS must be between 1 and 100000")
if MAX_CONCURRENT_TASKS < 1 or MAX_CONCURRENT_TASKS > 128:
    raise RuntimeError("MAX_CONCURRENT_TASKS must be between 1 and 128")
if not 0.05 <= AGENT_TIMEOUT_SECONDS <= 120:
    raise RuntimeError("AGENT_TIMEOUT_SECONDS must be between 0.05 and 120")

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(SERVICE_NAME)
app = FastAPI(title="Sky Agent Orchestrator", version="0.3.0")

ALLOWED_STAGES = ("plan", "execute", "review")


class TaskStatus(StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DispatchRequest(BaseModel):
    objective: str = Field(min_length=1, max_length=4000)
    stages: list[str] = Field(default_factory=lambda: list(ALLOWED_STAGES), min_length=1, max_length=3)

    @field_validator("objective")
    @classmethod
    def normalize_objective(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("objective must not be blank")
        return value

    @field_validator("stages")
    @classmethod
    def validate_stages(cls, values: list[str]) -> list[str]:
        normalized = [stage.strip().lower() for stage in values]
        if len(normalized) != len(set(normalized)):
            raise ValueError("stages must be unique")
        unsupported = [stage for stage in normalized if stage not in ALLOWED_STAGES]
        if unsupported:
            raise ValueError(f"unsupported stages: {', '.join(unsupported)}")
        return normalized


@dataclass
class TaskRecord:
    task_id: str
    objective: str
    stages: tuple[str, ...]
    status: TaskStatus
    current_stage: str | None
    completed_stages: int
    result: str | None
    error: str | None
    created_at: float


class TaskStore:
    def __init__(self, capacity: int) -> None:
        if capacity < 1:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self._records: dict[str, TaskRecord] = {}
        self._lock = Lock()

    def create(self, request: DispatchRequest) -> TaskRecord:
        with self._lock:
            if len(self._records) >= self.capacity:
                raise RuntimeError("task capacity reached")
            task_id = str(uuid4())
            record = TaskRecord(
                task_id=task_id,
                objective=request.objective,
                stages=tuple(request.stages),
                status=TaskStatus.QUEUED,
                current_stage=None,
                completed_stages=0,
                result=None,
                error=None,
                created_at=monotonic(),
            )
            self._records[task_id] = record
            return record

    def get(self, task_id: str) -> TaskRecord | None:
        with self._lock:
            record = self._records.get(task_id)
            return None if record is None else TaskRecord(**record.__dict__)

    def update(self, task_id: str, **changes: object) -> TaskRecord:
        with self._lock:
            record = self._records[task_id]
            for name, value in changes.items():
                setattr(record, name, value)
            return TaskRecord(**record.__dict__)

    def counts(self) -> dict[str, int]:
        with self._lock:
            counts = Counter(record.status.value for record in self._records.values())
            return {status.value: counts.get(status.value, 0) for status in TaskStatus}

    def size(self) -> int:
        with self._lock:
            return len(self._records)

    def clear(self) -> None:
        with self._lock:
            self._records.clear()


store = TaskStore(MAX_TASKS)
semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)


async def plan(value: str) -> str:
    return f"plan: define bounded steps for {value}"


async def execute(value: str) -> str:
    return f"execute: process approved plan -> {value}"


async def review(value: str) -> str:
    return f"review: verify deterministic result -> {value}"


HANDLERS = {"plan": plan, "execute": execute, "review": review}


def build_orchestrator(stages: tuple[str, ...]) -> Orchestrator:
    agents = [
        AgentSpec(stage, f"{stage} stage", stage, AGENT_TIMEOUT_SECONDS)
        for stage in stages
    ]
    return Orchestrator(agents, HANDLERS)


def serialize(record: TaskRecord) -> dict[str, object]:
    return {
        "task_id": record.task_id,
        "status": record.status.value,
        "current_stage": record.current_stage,
        "completed_stages": record.completed_stages,
        "total_stages": len(record.stages),
        "result": record.result,
        "error": record.error,
    }


async def execute_task(task_id: str) -> None:
    async with semaphore:
        try:
            record = store.get(task_id)
            if record is None:
                return
            store.update(task_id, status=TaskStatus.PROCESSING)
            orchestrator = build_orchestrator(record.stages)
            result = await orchestrator.run_workflow(record.objective)
            store.update(
                task_id,
                status=TaskStatus.COMPLETED,
                current_stage=None,
                completed_stages=len(result.steps),
                result=result.final_output,
            )
            logger.info("task_completed task_id=%s stages=%d duration_ms=%d", task_id, len(result.steps), result.duration_ms)
        except (WorkflowError, ValueError) as exc:
            logger.warning("task_failed task_id=%s error=%s", task_id, type(exc).__name__)
            if store.get(task_id) is not None:
                store.update(task_id, status=TaskStatus.FAILED, current_stage=None, error=str(exc))
        except Exception as exc:  # defensive task boundary
            logger.exception("task_failed task_id=%s", task_id)
            if store.get(task_id) is not None:
                store.update(task_id, status=TaskStatus.FAILED, current_stage=None, error=type(exc).__name__)


@app.get("/healthz")
def health() -> dict[str, str]:
    return {"status": "ok", "service": SERVICE_NAME}


@app.get("/readyz")
def ready() -> dict[str, object]:
    return {"status": "ready", "capacity": MAX_TASKS, "tasks": store.size(), "allowed_stages": list(ALLOWED_STAGES)}


@app.post("/api/v1/tasks", status_code=202)
async def dispatch(request: DispatchRequest, background_tasks: BackgroundTasks) -> dict[str, object]:
    try:
        record = store.create(request)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    background_tasks.add_task(execute_task, record.task_id)
    logger.info("task_queued task_id=%s stages=%d", record.task_id, len(record.stages))
    return serialize(record)


@app.get("/api/v1/tasks/{task_id}")
def status(task_id: str) -> dict[str, object]:
    try:
        UUID(task_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="task_id must be a UUID") from exc
    record = store.get(task_id)
    if record is None:
        raise HTTPException(status_code=404, detail="task not found")
    return serialize(record)


@app.get("/metrics")
def metrics() -> dict[str, object]:
    return {
        "service": SERVICE_NAME,
        "tasks": store.counts(),
        "capacity": MAX_TASKS,
        "max_concurrent_tasks": MAX_CONCURRENT_TASKS,
    }
