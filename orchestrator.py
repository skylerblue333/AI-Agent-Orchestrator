from __future__ import annotations

import asyncio
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Awaitable, Callable, Iterable

Handler = Callable[[str], Awaitable[str]]
_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class WorkflowError(RuntimeError):
    """Raised when a workflow cannot be executed safely."""


@dataclass(frozen=True)
class AgentSpec:
    name: str
    role: str
    handler: str
    timeout_seconds: float = 10.0

    def validate(self) -> None:
        if not _NAME_RE.fullmatch(self.name):
            raise ValueError("agent name must be 1-64 safe characters")
        if not self.role.strip() or len(self.role) > 120:
            raise ValueError("agent role must be 1-120 characters")
        if not _NAME_RE.fullmatch(self.handler):
            raise ValueError("handler name must be 1-64 safe characters")
        if not 0.05 <= self.timeout_seconds <= 120:
            raise ValueError("timeout_seconds must be between 0.05 and 120")


@dataclass(frozen=True)
class StepResult:
    agent: str
    role: str
    handler: str
    duration_ms: int
    output: str


@dataclass(frozen=True)
class WorkflowResult:
    objective: str
    final_output: str
    steps: tuple[StepResult, ...]
    duration_ms: int

    def to_dict(self) -> dict[str, object]:
        return {
            "objective": self.objective,
            "final_output": self.final_output,
            "duration_ms": self.duration_ms,
            "steps": [asdict(step) for step in self.steps],
        }


class Orchestrator:
    """Sequential, bounded coordinator for explicitly registered async handlers.

    The core does not execute arbitrary code or make implicit network/LLM calls.
    Integrators register handlers in-process and control any external side effects.
    """

    def __init__(
        self,
        agents: Iterable[AgentSpec],
        handlers: dict[str, Handler],
        *,
        max_objective_chars: int = 8_000,
        max_output_chars: int = 32_000,
    ) -> None:
        self.agents = tuple(agents)
        self.handlers = dict(handlers)
        self.max_objective_chars = max_objective_chars
        self.max_output_chars = max_output_chars
        self.logger = logging.getLogger("sky_orchestrator")
        if not 1 <= len(self.agents) <= 32:
            raise ValueError("workflow must contain between 1 and 32 agents")
        for agent in self.agents:
            agent.validate()
            if agent.handler not in self.handlers:
                raise ValueError(f"handler is not registered: {agent.handler}")
        if not 1 <= max_objective_chars <= 100_000:
            raise ValueError("max_objective_chars is out of range")
        if not 1 <= max_output_chars <= 200_000:
            raise ValueError("max_output_chars is out of range")

    async def run_workflow(self, objective: str) -> WorkflowResult:
        objective = objective.strip()
        if not objective:
            raise ValueError("objective must not be empty")
        if len(objective) > self.max_objective_chars:
            raise ValueError("objective exceeds configured size limit")

        workflow_started = time.perf_counter()
        context = objective
        results: list[StepResult] = []

        for agent in self.agents:
            started = time.perf_counter()
            try:
                output = await asyncio.wait_for(
                    self.handlers[agent.handler](context),
                    timeout=agent.timeout_seconds,
                )
            except TimeoutError as exc:
                self.logger.warning("agent_timeout agent=%s handler=%s", agent.name, agent.handler)
                raise WorkflowError(f"agent timed out: {agent.name}") from exc
            except Exception as exc:
                self.logger.exception("agent_failed agent=%s handler=%s", agent.name, agent.handler)
                raise WorkflowError(f"agent failed: {agent.name}") from exc

            if not isinstance(output, str):
                raise WorkflowError(f"agent returned non-string output: {agent.name}")
            output = output.strip()
            if not output:
                raise WorkflowError(f"agent returned empty output: {agent.name}")
            if len(output) > self.max_output_chars:
                raise WorkflowError(f"agent output exceeds configured size limit: {agent.name}")

            duration_ms = round((time.perf_counter() - started) * 1000)
            results.append(
                StepResult(
                    agent=agent.name,
                    role=agent.role,
                    handler=agent.handler,
                    duration_ms=duration_ms,
                    output=output,
                )
            )
            context = output
            self.logger.info(
                "agent_completed agent=%s handler=%s duration_ms=%s",
                agent.name,
                agent.handler,
                duration_ms,
            )

        return WorkflowResult(
            objective=objective,
            final_output=context,
            steps=tuple(results),
            duration_ms=round((time.perf_counter() - workflow_started) * 1000),
        )


async def prefix_handler(prefix: str, value: str) -> str:
    return f"{prefix}: {value}"
