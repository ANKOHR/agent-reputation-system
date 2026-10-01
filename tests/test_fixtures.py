import json
from agent_reputation_system.cli import atomic_write
from agent_reputation_system.core import aggregate
from agent_reputation_system.fixtures import EXPECTATIONS, fixture_records, fixture_files


def test_fixtures_labelled_synthetic(tmp_path):
    for name, content in fixture_files().items():
        atomic_write(tmp_path / name, content)
    content = (tmp_path / "records.jsonl").read_text(encoding="utf-8")
    assert content.startswith("# SYNTHETIC")
    rows = [json.loads(line) for line in content.splitlines()[1:]]
    assert len(rows) == 200 and all(r["synthetic"] is True for r in rows)
    expected = json.loads((tmp_path / "expectations.json").read_text())
    assert expected["synthetic"] is True
    assert "Synthetic" in expected["_comment"]


def test_fixture_ground_truth_matches_hand_computed():
    result, expected = aggregate(fixture_records()), EXPECTATIONS
    assert result["totals"] == expected["totals"]
    assert [{k: v for k, v in g.items() if k != "record_ids"} for g in result["by_agent_task"]] == expected["by_agent_task"]
    assert result["failure_ids"] == expected["failure_ids"]
    assert result["by_task_type"] == expected["by_task_type"]
