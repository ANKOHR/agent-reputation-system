"""Pure validation and aggregation. No prediction or illustrative metrics."""
from datetime import date
from fractions import Fraction
import re

DEFAULT_AS_OF = "2026-09-30"
FIELDS = {"id", "agent", "task_type", "outcome", "completed_at", "synthetic", "entered_by"}


class SchemaError(ValueError):
    """An explicit record violates the input contract."""


def validate_record(record, as_of=DEFAULT_AS_OF):
    if not isinstance(record, dict):
        raise SchemaError("record: expected an object")
    missing = FIELDS - {"entered_by"} - record.keys()
    extra = record.keys() - FIELDS
    if missing or extra:
        raise SchemaError(f"fields: missing={sorted(missing)}, unknown={sorted(extra)}")
    for field in ("id", "agent", "task_type"):
        value = record[field]
        if not isinstance(value, str) or not value.strip() or len(value) > 4096:
            raise SchemaError(f"{field}: expected nonblank string of at most 4096 characters")
        if any(ord(c) < 32 or ord(c) == 127 or c == "\u2014" for c in value):
            raise SchemaError(f"{field}: control characters and U+2014 are forbidden")
    if record["outcome"] not in ("success", "failure"):
        raise SchemaError("outcome: expected success or failure")
    if type(record["synthetic"]) is not bool:
        raise SchemaError("synthetic: expected boolean")
    if not record["synthetic"] and record.get("entered_by") != "Henry":
        raise SchemaError("entered_by: real input requires Henry's explicit attestation")
    if record["synthetic"] and "entered_by" in record:
        raise SchemaError("entered_by: must be absent for synthetic records")
    value = record["completed_at"]
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise SchemaError("completed_at: expected ISO date YYYY-MM-DD")
    try:
        completed = date.fromisoformat(value)
        cutoff = date.fromisoformat(as_of)
    except (ValueError, TypeError):
        raise SchemaError("completed_at/as_of: invalid calendar date") from None
    if completed > cutoff:
        raise SchemaError(f"completed_at: future date relative to as_of={as_of}")
    return dict(record)


def tally(records):
    total = len(records)
    success = sum(r["outcome"] == "success" for r in records)
    ratio = Fraction(success, total) if total else None
    return {"total": total, "successes": success, "failures": total - success,
            "success_rate_exact": str(ratio) if ratio is not None else None}


def aggregate(records, as_of=DEFAULT_AS_OF):
    """Return exact observed counts and fractions; no forecasts or savings."""
    try:
        if date.fromisoformat(as_of).isoformat() != as_of:
            raise ValueError()
    except (ValueError, TypeError):
        raise SchemaError("as_of: expected ISO calendar date YYYY-MM-DD") from None
    checked = []
    seen = set()
    for record in records:
        item = validate_record(record, as_of)
        if item["id"] in seen:
            raise SchemaError(f"id: duplicate {item['id']!r}")
        seen.add(item["id"])
        checked.append(item)
    checked.sort(key=lambda r: r["id"])
    groups = []
    for agent, task in sorted({(r["agent"], r["task_type"]) for r in checked}):
        subset = [r for r in checked if r["agent"] == agent and r["task_type"] == task]
        groups.append({"agent": agent, "task_type": task, **tally(subset)})
    tasks = [{"task_type": task, **tally([r for r in checked if r["task_type"] == task])}
             for task in sorted({r["task_type"] for r in checked})]
    return {"as_of": as_of, "totals": tally(checked), "by_agent_task": groups,
            "by_task_type": tasks, "failure_ids": [r["id"] for r in checked if r["outcome"] == "failure"],
            "records": checked,
            "provenance": {"synthetic_records": sum(r["synthetic"] for r in checked),
                           "real_henry_entered_records": sum(not r["synthetic"] for r in checked)}}


def rank_groups(result, task_type=None):
    """Order observed rates, then sample size, then agent/task; not a prediction."""
    groups = [g for g in result["by_agent_task"] if task_type is None or g["task_type"] == task_type]
    return sorted(groups, key=lambda g: (-Fraction(g["successes"], g["total"]),
                                         -g["total"], g["agent"], g["task_type"]))
