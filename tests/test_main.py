import json
import subprocess
import sys


def test_cli_returns_structured_json() -> None:
    completed = subprocess.run(
        [sys.executable, "orchestrator.py", "release review"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(completed.stdout)
    assert payload["objective"] == "release review"
    assert payload["output"] == "review: synthesis: research: release review"
    assert [step["agent"] for step in payload["steps"]] == [
        "research",
        "synthesis",
        "review",
    ]
