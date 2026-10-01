import pytest
from agent_reputation_system.core import SchemaError, aggregate
from agent_reputation_system.fixtures import fixture_records


@pytest.mark.parametrize("field,value", [("amount", -1), ("completed_at", "2099-01-01"),
    ("agent", "x" * 4097), ("outcome", "unknown"), ("synthetic", 1),
    ("id", ""), ("agent", "a\u2014b"), ("completed_at", "20260901"), ("task_type", "a\nb")])
def test_rejects_adversarial_values(field, value):
    row = fixture_records()[0]
    row[field] = value
    with pytest.raises(SchemaError):
        aggregate([row])


def test_duplicate_ids_rejected():
    row = fixture_records()[0]
    with pytest.raises(SchemaError, match="duplicate"):
        aggregate([row, row])


def test_handles_unicode_and_long_inputs():
    row = fixture_records()[0]
    row["agent"] = "亨利 café " + "x" * 4000
    row["task_type"] = r"C:\Users\henry\任务"
    assert aggregate([row])["by_agent_task"][0]["agent"] == row["agent"]


def test_corrupted_ground_truth_changes_computed_result():
    rows = fixture_records()
    before = aggregate(rows)
    rows[0]["outcome"] = "failure"
    after = aggregate(rows)
    assert after["totals"]["successes"] == before["totals"]["successes"] - 1
    assert "trial-001" in after["failure_ids"]


def test_real_and_synthetic_are_counted_separately():
    rows = fixture_records()[:2]
    rows[0]["synthetic"] = False
    rows[0]["entered_by"] = "Henry"
    assert aggregate(rows)["provenance"] == {"real_henry_entered_records": 1, "synthetic_records": 1}
