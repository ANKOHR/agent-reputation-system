import json
from agent_reputation_system.core import aggregate
from agent_reputation_system.fixtures import fixture_records, EXPECTATIONS
from agent_reputation_system.report import render


def test_report_matches_ground_truth_exact():
    report = json.loads(render(aggregate(fixture_records()), "json"))
    assert report["totals"] == EXPECTATIONS["totals"]
    assert "29/40" in render(aggregate(fixture_records()))


def test_report_zero_false_positives():
    report = json.loads(render(aggregate(fixture_records()), "json"))
    assert set(report["failure_ids"]) == set(EXPECTATIONS["failure_ids"])


def test_report_carries_provenance_banner():
    for format in ("md", "json"):
        output = render(aggregate(fixture_records()), format)
        assert "200 synthetic fixture records" in output
        assert "0 real records" in output


def test_hypothetical_figures_labelled():
    for format in ("md", "json"):
        assert "No predictions or measured time/money savings" in render(aggregate([]), format)


def test_no_em_dashes_in_outputs():
    for format in ("md", "json"):
        assert "\u2014" not in render(aggregate(fixture_records()), format)


def test_markdown_escapes_input():
    row = fixture_records()[0]
    row["agent"] = "<script>|name"
    assert "&lt;script&gt;&#124;name" in render(aggregate([row]))
