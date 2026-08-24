import asyncio

import pytest

from orchestrator import AgentSpec, Orchestrator, WorkflowError


@pytest.mark.asyncio
async def test_workflow_runs_in_declared_order() -> None:
    async def first(value: str) -> str:
        return f"first({value})"

    async def second(value: str) -> str:
        return f"second({value})"

    orchestrator = Orchestrator(
        [AgentSpec("a", "first", "first"), AgentSpec("b", "second", "second")],
        {"first": first, "second": second},
    )
    result = await orchestrator.run_workflow("goal")
    assert result.final_output == "second(first(goal))"
    assert [step.agent for step in result.steps] == ["a", "b"]


@pytest.mark.asyncio
async def test_timeout_is_fail_closed() -> None:
    async def slow(value: str) -> str:
        await asyncio.sleep(0.05)
        return value

    orchestrator = Orchestrator(
        [AgentSpec("slow", "slow", "slow", timeout_seconds=0.01)],
        {"slow": slow},
    )
    with pytest.raises(WorkflowError, match="timed out"):
        await orchestrator.run_workflow("goal")


@pytest.mark.asyncio
async def test_empty_output_is_rejected() -> None:
    async def empty(_: str) -> str:
        return "   "

    orchestrator = Orchestrator([AgentSpec("a", "role", "empty")], {"empty": empty})
    with pytest.raises(WorkflowError, match="empty output"):
        await orchestrator.run_workflow("goal")


def test_unregistered_handler_is_rejected() -> None:
    with pytest.raises(ValueError, match="not registered"):
        Orchestrator([AgentSpec("a", "role", "missing")], {})


@pytest.mark.asyncio
async def test_objective_size_is_bounded() -> None:
    async def passthrough(value: str) -> str:
        return value

    orchestrator = Orchestrator(
        [AgentSpec("a", "role", "pass")],
        {"pass": passthrough},
        max_objective_chars=4,
    )
    with pytest.raises(ValueError, match="size limit"):
        await orchestrator.run_workflow("12345")
