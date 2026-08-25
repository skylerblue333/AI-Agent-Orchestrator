import asyncio

import pytest

from orchestrator import Agent, Orchestrator, StepAuthorization, demo_orchestrator


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


def test_policy_contract_matches_skypolicy_shape() -> None:
    request = StepAuthorization("user:42", "agents.execute", "agent:review")
    assert request.to_policy_request() == {
        "principal": "user:42",
        "action": "agents.execute",
        "resource": "agent:review",
    }


def test_policy_decider_is_called_for_each_step() -> None:
    async def echo(value: str) -> str:
        return value

    requests: list[StepAuthorization] = []

    def allow(request: StepAuthorization) -> bool:
        requests.append(request)
        return True

    orchestrator = Orchestrator(
        [Agent("first", "worker", echo), Agent("second", "reviewer", echo)],
        principal="user:42",
        policy_decider=allow,
    )
    asyncio.run(orchestrator.run_workflow("work"))

    assert [request.to_policy_request() for request in requests] == [
        {"principal": "user:42", "action": "agents.execute", "resource": "agent:first"},
        {"principal": "user:42", "action": "agents.execute", "resource": "agent:second"},
    ]


def test_policy_denial_prevents_handler_execution() -> None:
    executed = False

    async def handler(value: str) -> str:
        nonlocal executed
        executed = True
        return value

    orchestrator = Orchestrator(
        [Agent("restricted", "worker", handler)],
        principal="user:42",
        policy_decider=lambda _request: False,
    )

    with pytest.raises(PermissionError, match="policy denied"):
        asyncio.run(orchestrator.run_workflow("work"))
    assert executed is False


def test_rejects_empty_principal() -> None:
    async def echo(value: str) -> str:
        return value

    with pytest.raises(ValueError, match="principal"):
        Orchestrator([Agent("echo", "worker", echo)], principal="   ")
