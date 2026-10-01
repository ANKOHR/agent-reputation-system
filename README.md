# Agent Reputation System

`ars` computes observed agent reliability by task type from explicit local outcomes. Hypothesis: deterministic accounting, pinned to independent ground truth and provenance, gives operators trustworthy historical results. Synthetic acceptance validates the implementation, not agent competence or business value.

## Quickstart

Python 3.10 or later, setuptools already installed, pytest for tests. Runtime has no third-party dependencies. CPU only, local files only, no model calls, network calls, GPU packages or database server.

```powershell
python -m pip install --no-build-isolation --no-deps --no-index -e .
ars fixtures --out demo
ars run --input demo
ars report --format md
python -m pytest -q
```

If your Python Scripts directory is absent from PATH, use `python -m agent_reputation_system.cli` in place of `ars`, or add the user Scripts directory to PATH. On shells with `&&`, the demo is `ars fixtures --out demo && ars run --input demo && ars report --format md`. Fixture output must be a new directory, so choose another path for repeat generation.

Smallest hand-written example:

```powershell
ars run --input examples/five-records
ars report --format json
```

Those five synthetic observations yield 3 successes, 2 failures and exact success fraction 3/5. They are not real operating evidence.

## Input format reference

An input directory can contain UTF-8 JSONL, JSON arrays or CSV. YAML is rejected with a named error and a conversion hint. `expectations.json` and `README.md` are reserved metadata, ignored by the engine. Subdirectories are ignored; processing is not recursive. Unknown file extensions are rejected. JSONL permits blank lines and lines beginning with `#` as comments.

```json
{"id":"example-1","agent":"atlas","task_type":"coding","outcome":"success","completed_at":"2026-09-01","synthetic":true}
```

This example is synthetic. Every row requires:

| Field | Rule |
| --- | --- |
| id | Unique across all files in the run |
| agent | Exact agent name, case sensitive |
| task_type | Exact task category, case sensitive |
| outcome | `success` or `failure`, using a consistent task acceptance criterion |
| completed_at | Exact ISO YYYY-MM-DD, no later than `--as-of` |
| synthetic | Boolean, true for fixtures, false only for actual recorded observations |
| entered_by | Must be `Henry` for real records; must be absent for synthetic records |

`entered_by` is an input attestation, not independently verified authorship. Henry can hand-enter real observations into a private local directory; do not ship trial data. All unknown fields, including negative amounts, are rejected. Money and savings are not part of the schema.

IDs and names must be nonblank strings of at most 4096 characters. Unicode and Windows paths are supported. Control characters and U+2014 are prohibited. Names are preserved without trimming or normalization. Duplicate JSON keys and nonfinite JSON constants are parse errors. CSV uses the same field names and literal `true`/`false` for synthetic; an empty entered_by cell is removed. CSV headers are validated even when no rows follow.

The fixed default reference date is 2026-09-30. For later observations use `--as-of YYYY-MM-DD`. The program never reads the wall clock to validate dates. No randomness is used, so a random seed is not applicable. Identical input bytes and arguments produce byte-identical stored results and reports.

## Subcommand catalogue

| Command | Example | Behavior |
| --- | --- | --- |
| fixtures | `ars fixtures --out demo` | Stage and publish a new local directory containing 200 synthetic records and independent expectations |
| run | `ars run --input demo --as-of 2026-09-30 --state local/results.json` | Validate all observations, compute, atomically save snapshot |
| report | `ars report --format json --out report.json` | Markdown or JSON report with provenance and traceability |
| rank | `ars rank --task-type coding` | Rank observed fractions, then sample size, then lexical agent/task; not a prediction |
| failures | `ars failures --task-type research` | List explicit failure records with provenance |

Every command has `--help` and examples. `run`, `report`, `rank` and `failures` accept `--state` after the subcommand; default `.ars/results.json`. Report, rank and failures accept `--format md|json` and `--out`. Task filters match exact strings. Ranking output gives full-snapshot provenance counts even when filtered. Empty task selections have no rows, not invented scores.

Reports read the last successful snapshot, not live input files. Rerun after changing observations. Snapshots contain original normalized records, source filenames, SHA-256 hashes, reference date and computed counts. When read, aggregates are recomputed from the stored records and inconsistent snapshots are rejected. Hashes record input identity at run time; they do not authenticate authorship or prove the source files still exist.

## Calculation and architecture

Success fraction = successes / attempts, reduced with exact rational arithmetic. `total` is the attempt count. Failures = attempts - successes. Zero attempts gives a null fraction in JSON and an N/A label in Markdown. Groups are reported per agent/task pair and per task type. Observed rankings do not establish future performance; sample size remains visible.

```text
fixtures.py -> labelled JSONL + independent expectations + fixture README
local JSONL / JSON / CSV -> cli.py (parse, validate, hash)
                        -> core.py (pure aggregation, exact fractions)
                        -> atomic local snapshot
                        -> report.py -> Markdown / JSON
```

## Honesty boundary and fixture labelling

The tool computes from explicit inputs; it does not discover, predict or estimate beyond them. Outcomes and real-data authorship are author-declared, not independently verified. Time and money savings are unmeasured and are not reported. Hypothetical or illustrative savings are explicitly described as not computed. Mixed real and synthetic input has separate provenance counts, but its combined totals must not be treated as a real-world evaluation. Every report, including filtered and empty reports, carries the provenance banner.

Every fixture record has `synthetic: true`; JSONL begins with a SYNTHETIC header. JSON expectations contain `synthetic: true` and an explanatory `_comment`, since JSON has no comments. The fixture README and five-record example also carry synthetic header comments. Never remove these labels when sharing results.

Four blocks of 50 contain 45, 35, 40 and 25 successes respectively for atlas/coding, atlas/research, beacon/coding and beacon/research. Hand arithmetic: 145 successes, 55 failures, fraction 29/40. Coding totals are 85/100 = 17/20; research totals are 60/100 = 3/5. Failure IDs are trial-046 through trial-050, trial-086 through trial-100, trial-141 through trial-150 and trial-176 through trial-200. Expectations are independent constants in fixtures.py; the engine ignores expectations.json. Deliberately changing an outcome changes the report.

## Failure modes and acceptance

ParseError identifies malformed JSON/CSV, file and line; JSON syntax errors identify the physical line, while schema errors for a JSON array identify document origin line 1. JSONL and CSV schema errors identify record lines. SchemaError names missing or unknown fields, duplicate IDs, invalid dates, unsupported YAML or schema drift. MissingInput includes a usage hint; MissingResults tells the user to run first. Invalid UTF-8 and unreadable sources produce named errors. WriteError names bad output paths. Output writes use temporary files and atomic replacement; failed writes leave no partial files, and a bad run preserves the prior snapshot. Fixture creation stages the whole directory and refuses to overwrite an existing directory.

Empty input produces zero totals without a traceback. The acceptance suite checks planted ground truth, zero false positives, exact reconciliation, corruption sensitivity, deterministic bytes, provenance, malformed and missing inputs, duplicate IDs, future dates, adversarial values, Unicode, long names, Windows paths and write failures. See EVIDENCE.md for locally measured test and demo results. Those results apply to controlled fixtures, not unknown real data quality.

## Evidence-based improvement hook

Begin the 14-day window on first real use. Privately record run dates, daily usage, a frozen hand-checked sample, checked output counts and mismatched counts. Primary metric: discrepancy rate = mismatched hand-checked output counts / checked output counts. Compare manual grouping and the CLI on identical input and acceptance criteria. Zero checked counts means unmeasured, not zero error. Measure both workflows against a baseline before claiming any time saved.

If discrepancy rate exceeds 10 percent, fix the largest observed failure cause and recheck, or kill with a recorded reason. If unused, record that and kill. After the window write the explicit verdict in VERDICT.md with evidence: expand for daily use or revenue; integrate for substantial sibling overlap; commercialise if a buyer would pay as-is; maintain as portfolio evidence otherwise; kill if unused or unable to meet acceptance. No real usage evidence exists at build time, so the operating verdict remains pending rather than invented.
