import asyncio

import pytest

from orchestrator import Agent, Orchestrator, demo_orchestrator


def test_demo_workflow_is_deterministic() -> None:
    result = asyncio.run(demo_orchestrator().run_workflow("ship safely"))
    assert result.objective == "ship safely"
    assert [step.agent for step in result.steps] == ["research", "synthesis", "review"]
    assert result.output == "review: synthesis: research: ship safely"


def test_rejects_duplicate_agents() -> None:
    async def echo(value: str) -> str:
        return value

    with pytest.raises(ValueError, match="unique"):
        Orchestrator([Agent("same", "one", echo), Agent("same", "two", echo)])


def test_rejects_empty_objective() -> None:
    async def echo(value: str) -> str:
        return value

    orchestrator = Orchestrator([Agent("echo", "worker", echo)])
    with pytest.raises(ValueError, match="objective"):
        asyncio.run(orchestrator.run_workflow("   "))


def test_rejects_empty_agent_output() -> None:
    async def empty(_: str) -> str:
        return " "

    orchestrator = Orchestrator([Agent("empty", "worker", empty)])
    with pytest.raises(ValueError, match="empty output"):
        asyncio.run(orchestrator.run_workflow("work"))


def test_agent_timeout_is_bounded() -> None:
    async def slow(value: str) -> str:
        await asyncio.sleep(0.05)
        return value

    orchestrator = Orchestrator([Agent("slow", "worker", slow, timeout_seconds=0.001)])
    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(orchestrator.run_workflow("work"))
