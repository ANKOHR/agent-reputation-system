"""Deterministic rendering with provenance on every report surface."""
import json


def banner(result):
    p = result["provenance"]
    return (f"DATA PROVENANCE: {p['synthetic_records']} synthetic fixture records; "
            f"{p['real_henry_entered_records']} real records attested as entered by Henry. "
            "Computed observed outcomes only. No predictions or measured time/money savings.")


def escape(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("`", "&#96;").replace("\\", "&#92;")


def render(result, format="md"):
    if format == "json":
        return json.dumps({"banner": banner(result), "measurement_scope": "Observed input outcomes only; savings unmeasured and not reported.", **result},
                          sort_keys=True, ensure_ascii=False, indent=2) + "\n"
    if format != "md":
        raise ValueError("format: expected md or json")
    t = result["totals"]
    lines = ["# Agent Reputation System", "", banner(result), "",
             f"As of: {result['as_of']}", "",
             f"Records: {t['total']}; successes: {t['successes']}; failures: {t['failures']}; "
             f"exact success rate: {t['success_rate_exact'] or 'N/A (no observations)' }.", "",
             "Rates are exact fractions, descriptive only. Small samples do not establish future reliability.", "",
             "| Agent | Task type | Records | Successes | Failures | Exact success rate |",
             "| --- | --- | ---: | ---: | ---: | --- |"]
    for g in result["by_agent_task"]:
        lines.append("| " + " | ".join(escape(g[k]) for k in ("agent", "task_type", "total", "successes", "failures", "success_rate_exact")) + " |")
    lines += ["", "## Task totals", "", "| Task type | Records | Successes | Failures | Exact success rate |",
              "| --- | ---: | ---: | ---: | --- |"]
    for g in result["by_task_type"]:
        lines.append("| " + " | ".join(escape(g[k]) for k in ("task_type", "total", "successes", "failures", "success_rate_exact")) + " |")
    lines += ["", "## Traceability", "", "Input files (SHA-256):"]
    for source in result.get("inputs", []):
        lines.append(f"- {escape(source['file'])}: {source['sha256']}; {source['records']} records")
    lines += ["", "Observed failure IDs: " + (", ".join(escape(v) for v in result["failure_ids"]) or "none"), "",
              "Hypothetical or illustrative savings: not computed. No baseline measurements were supplied.", ""]
    return "\n".join(lines)
