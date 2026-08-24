from __future__ import annotations

import argparse
import asyncio
import json
import logging
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import asdict, dataclass

LOGGER = logging.getLogger("sky-agent-orchestrator")
MAX_OBJECTIVE_CHARS = 10_000
MAX_AGENTS = 32
AgentHandler = Callable[[str], Awaitable[str]]


@dataclass(frozen=True)
class Agent:
    name: str
    role: str
    handler: AgentHandler
    timeout_seconds: float = 30.0

    def validate(self) -> None:
        if not self.name.strip() or not self.role.strip():
            raise ValueError("agent name and role must be non-empty")
        if self.timeout_seconds <= 0 or self.timeout_seconds > 300:
            raise ValueError("agent timeout_seconds must be in (0, 300]")


@dataclass(frozen=True)
class StepResult:
    agent: str
    role: str
    output: str


@dataclass(frozen=True)
class WorkflowResult:
    objective: str
    steps: tuple[StepResult, ...]
    output: str

    def to_json(self) -> str:
        return json.dumps(asdict(self), separators=(",", ":"), ensure_ascii=False)


class Orchestrator:
    """Execute a bounded sequence of injected asynchronous agent handlers."""

    def __init__(self, agents: Sequence[Agent]) -> None:
        if not agents:
            raise ValueError("at least one agent is required")
        if len(agents) > MAX_AGENTS:
            raise ValueError(f"at most {MAX_AGENTS} agents are allowed")
        names = [agent.name.strip() for agent in agents]
        if len(names) != len(set(names)):
            raise ValueError("agent names must be unique")
        for agent in agents:
            agent.validate()
        self._agents = tuple(agents)

    async def run_workflow(self, objective: str) -> WorkflowResult:
        objective = objective.strip()
        if not objective:
            raise ValueError("objective must be non-empty")
        if len(objective) > MAX_OBJECTIVE_CHARS:
            raise ValueError(f"objective exceeds {MAX_OBJECTIVE_CHARS} characters")

        context = objective
        results: list[StepResult] = []
        for agent in self._agents:
            LOGGER.info("agent_step_start agent=%s role=%s", agent.name, agent.role)
            try:
                output = await asyncio.wait_for(
                    agent.handler(context), timeout=agent.timeout_seconds
                )
            except asyncio.TimeoutError as exc:
                raise TimeoutError(f"agent {agent.name!r} timed out") from exc
            if not isinstance(output, str) or not output.strip():
                raise ValueError(f"agent {agent.name!r} returned an empty output")
            context = output.strip()
            results.append(StepResult(agent.name, agent.role, context))
            LOGGER.info("agent_step_complete agent=%s", agent.name)

        return WorkflowResult(objective, tuple(results), context)


async def _prefix_handler(prefix: str, value: str) -> str:
    return f"{prefix}: {value}"


def demo_orchestrator() -> Orchestrator:
    return Orchestrator(
        [
            Agent("research", "researcher", lambda value: _prefix_handler("research", value)),
            Agent("synthesis", "synthesizer", lambda value: _prefix_handler("synthesis", value)),
            Agent("review", "reviewer", lambda value: _prefix_handler("review", value)),
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the deterministic Sky Agent workflow demo")
    parser.add_argument("objective", help="workflow objective")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    result = asyncio.run(demo_orchestrator().run_workflow(args.objective))
    print(result.to_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
