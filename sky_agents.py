from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass

MAX_TASKS = 64
MAX_TOKEN_CHARS = 128
MAX_PAYLOAD_CHARS = 20_000
AgentHandler = Callable[[str], Awaitable[str]]


def _token(value: str, field: str) -> str:
    if not isinstance(value, str):
        raise TypeError(f"{field} must be a string")
    value = value.strip()
    if not value or len(value) > MAX_TOKEN_CHARS or any(ch.isspace() for ch in value):
        raise ValueError(f"{field} must be a non-empty bounded token without whitespace")
    return value


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    agent_id: str
    payload: str
    timeout_seconds: float = 30.0

    def normalized(self) -> "AgentTask":
        task_id = _token(self.task_id, "task_id")
        agent_id = _token(self.agent_id, "agent_id")
        if not isinstance(self.payload, str):
            raise TypeError("payload must be a string")
        payload = self.payload.strip()
        if not payload or len(payload) > MAX_PAYLOAD_CHARS:
            raise ValueError(f"payload must contain 1-{MAX_PAYLOAD_CHARS} characters")
        if not isinstance(self.timeout_seconds, (int, float)) or not 0 < self.timeout_seconds <= 300:
            raise ValueError("timeout_seconds must be in (0, 300]")
        return AgentTask(task_id, agent_id, payload, float(self.timeout_seconds))


@dataclass(frozen=True)
class AgentTaskResult:
    task_id: str
    agent_id: str
    output: str


class AgentRegistry:
    """In-memory registry for caller-provided asynchronous handlers."""

    def __init__(self, handlers: Mapping[str, AgentHandler]) -> None:
        if not handlers:
            raise ValueError("at least one handler is required")
        normalized: dict[str, AgentHandler] = {}
        for agent_id, handler in handlers.items():
            key = _token(agent_id, "agent_id")
            if not callable(handler):
                raise TypeError(f"handler for {key!r} must be callable")
            if key in normalized:
                raise ValueError(f"duplicate agent_id: {key}")
            normalized[key] = handler
        self._handlers = normalized

    async def execute(self, tasks: Sequence[AgentTask]) -> tuple[AgentTaskResult, ...]:
        if not isinstance(tasks, Sequence) or isinstance(tasks, (str, bytes)):
            raise TypeError("tasks must be a sequence")
        if not tasks or len(tasks) > MAX_TASKS:
            raise ValueError(f"tasks must contain 1-{MAX_TASKS} entries")
        normalized = [task.normalized() for task in tasks]
        ids = [task.task_id for task in normalized]
        if len(ids) != len(set(ids)):
            raise ValueError("task_id values must be unique")

        results: list[AgentTaskResult] = []
        for task in normalized:
            handler = self._handlers.get(task.agent_id)
            if handler is None:
                raise KeyError(f"unknown agent_id: {task.agent_id}")
            try:
                output = await asyncio.wait_for(handler(task.payload), timeout=task.timeout_seconds)
            except asyncio.TimeoutError as exc:
                raise TimeoutError(f"task {task.task_id!r} timed out") from exc
            if not isinstance(output, str) or not output.strip():
                raise ValueError(f"task {task.task_id!r} returned empty output")
            results.append(AgentTaskResult(task.task_id, task.agent_id, output.strip()))
        return tuple(results)
