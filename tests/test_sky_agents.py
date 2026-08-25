import asyncio

import pytest

from sky_agents import AgentRegistry, AgentTask


async def upper(value: str) -> str:
    return value.upper()


async def prefix(value: str) -> str:
    return f"review:{value}"


def test_executes_explicit_tasks_in_order() -> None:
    registry = AgentRegistry({"upper": upper, "review": prefix})
    results = asyncio.run(
        registry.execute(
            [
                AgentTask("t1", "upper", "hello"),
                AgentTask("t2", "review", "done"),
            ]
        )
    )
    assert [(r.task_id, r.agent_id, r.output) for r in results] == [
        ("t1", "upper", "HELLO"),
        ("t2", "review", "review:done"),
    ]


def test_rejects_unknown_agent() -> None:
    registry = AgentRegistry({"upper": upper})
    with pytest.raises(KeyError, match="unknown agent_id"):
        asyncio.run(registry.execute([AgentTask("t1", "missing", "hello")]))


def test_rejects_duplicate_task_ids() -> None:
    registry = AgentRegistry({"upper": upper})
    with pytest.raises(ValueError, match="unique"):
        asyncio.run(
            registry.execute(
                [AgentTask("same", "upper", "a"), AgentTask("same", "upper", "b")]
            )
        )


def test_rejects_unbounded_or_malformed_input() -> None:
    registry = AgentRegistry({"upper": upper})
    with pytest.raises(ValueError, match="bounded token"):
        asyncio.run(registry.execute([AgentTask("bad id", "upper", "hello")]))
    with pytest.raises(ValueError, match="payload"):
        asyncio.run(registry.execute([AgentTask("t1", "upper", "   ")]))


def test_timeout_fails_closed() -> None:
    async def slow(value: str) -> str:
        await asyncio.sleep(0.05)
        return value

    registry = AgentRegistry({"slow": slow})
    with pytest.raises(TimeoutError, match="timed out"):
        asyncio.run(registry.execute([AgentTask("t1", "slow", "hello", 0.001)]))
