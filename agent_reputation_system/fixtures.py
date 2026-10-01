"""Labelled deterministic fixtures; no randomness (seed: not applicable)."""
import json

# Independently hand-computed: four blocks of 50, with 45/35/40/25 successes.
EXPECTATIONS = {
    "_comment": "Synthetic planted ground truth, hand-computed from four blocks of 50.",
    "synthetic": True,
    "totals": {"total": 200, "successes": 145, "failures": 55, "success_rate_exact": "29/40"},
    "by_agent_task": [
        {"agent": "atlas", "task_type": "coding", "total": 50, "successes": 45, "failures": 5, "success_rate_exact": "9/10"},
        {"agent": "atlas", "task_type": "research", "total": 50, "successes": 35, "failures": 15, "success_rate_exact": "7/10"},
        {"agent": "beacon", "task_type": "coding", "total": 50, "successes": 40, "failures": 10, "success_rate_exact": "4/5"},
        {"agent": "beacon", "task_type": "research", "total": 50, "successes": 25, "failures": 25, "success_rate_exact": "1/2"}],
    "by_task_type": [
        {"task_type": "coding", "total": 100, "successes": 85, "failures": 15, "success_rate_exact": "17/20"},
        {"task_type": "research", "total": 100, "successes": 60, "failures": 40, "success_rate_exact": "3/5"}],
    "failure_ids": [f"trial-{n:03d}" for n in [*range(46, 51), *range(86, 101), *range(141, 151), *range(176, 201)]]}


def fixture_records():
    records = []
    for block, (agent, task, successes) in enumerate([
            ("atlas", "coding", 45), ("atlas", "research", 35),
            ("beacon", "coding", 40), ("beacon", "research", 25)]):
        for index in range(1, 51):
            records.append({"id": f"trial-{block * 50 + index:03d}", "agent": agent,
                            "task_type": task, "outcome": "success" if index <= successes else "failure",
                            "completed_at": "2026-09-29", "synthetic": True})
    return records


def fixture_files():
    return {
        "records.jsonl": "# SYNTHETIC FIXTURE: planted outcomes, not real agent performance.\n" +
            "".join(json.dumps(r, sort_keys=True, ensure_ascii=False) + "\n" for r in fixture_records()),
        "expectations.json": json.dumps(EXPECTATIONS, sort_keys=True, indent=2) + "\n",
        "README.md": "<!-- SYNTHETIC FIXTURE -->\n# Synthetic fixture\n200 planted records. Not real performance. expectations.json is independently hand-computed.\n"}
