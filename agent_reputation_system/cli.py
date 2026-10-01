"""Local-only CLI. State commits atomically after all inputs validate."""
import argparse
import csv
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile

from .core import DEFAULT_AS_OF, FIELDS, SchemaError, aggregate, rank_groups, validate_record
from .fixtures import fixture_files
from .report import banner, render


class InputError(ValueError):
    """Named parse, schema, or file error with location."""


def json_load(text, name, line=1):
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                raise ValueError(f"duplicate JSON field {key!r}")
            obj[key] = value
        return obj
    try:
        return json.loads(text, object_pairs_hook=pairs,
                          parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"nonfinite value {value}")))
    except json.JSONDecodeError as exc:
        raise InputError(f"ParseError: {name}:line {line + exc.lineno - 1}: {exc.msg}") from None
    except ValueError as exc:
        raise InputError(f"ParseError: {name}:line {line}: {exc}") from None


def load_inputs(directory, as_of):
    root = Path(directory)
    if not root.is_dir():
        raise InputError(f"MissingInput: {root}: use ars run --input <existing directory>")
    records, inputs, seen = [], [], set()
    for path in sorted(root.iterdir(), key=lambda p: p.name):
        if path.name in ("expectations.json", "README.md") or path.is_dir():
            continue
        if any(ord(c) < 32 or c == "\u2014" for c in path.name):
            raise InputError("SchemaError: input filename contains prohibited characters")
        if path.suffix.lower() not in (".jsonl", ".json", ".csv", ".yaml", ".yml"):
            raise InputError(f"SchemaError: {path.name}:line 1: unsupported input file extension")
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8-sig")
        except (OSError, UnicodeError) as exc:
            raise InputError(f"ParseError: {path.name}:line 1: {exc}") from None
        entries = []
        if path.suffix.lower() == ".jsonl":
            for number, line in enumerate(text.splitlines(), 1):
                if line.strip() and not line.lstrip().startswith("#"):
                    entries.append((number, json_load(line, path.name, number)))
        elif path.suffix.lower() == ".json":
            value = json_load(text, path.name)
            if not isinstance(value, list):
                raise InputError(f"SchemaError: {path.name}:line 1: JSON input must be an array of records")
            # Index is provided for arrays; line is the JSON document origin.
            entries = [(1, record) for record in value]
        elif path.suffix.lower() == ".csv":
            try:
                reader = csv.DictReader(io.StringIO(text), strict=True)
                if not reader.fieldnames or len(reader.fieldnames) != len(set(reader.fieldnames)):
                    raise InputError(f"SchemaError: {path.name}:line 1: missing or duplicate CSV columns")
                missing = FIELDS - {"entered_by"} - set(reader.fieldnames)
                extra = set(reader.fieldnames) - FIELDS
                if missing or extra:
                    raise InputError(f"SchemaError: {path.name}:line 1: fields: missing={sorted(missing)}, unknown={sorted(extra)}")
                for record in reader:
                    number = reader.line_num
                    if None in record or any(value is None for value in record.values()):
                        raise InputError(f"ParseError: {path.name}:line {number}: inconsistent CSV columns")
                    if record.get("synthetic") not in ("true", "false"):
                        raise InputError(f"SchemaError: {path.name}:line {number}: synthetic must be true or false")
                    record["synthetic"] = record["synthetic"] == "true"
                    if record.get("entered_by") == "":
                        record.pop("entered_by")
                    entries.append((number, record))
            except csv.Error as exc:
                raise InputError(f"ParseError: {path.name}:line {reader.line_num}: {exc}") from None
        else:
            raise InputError(f"SchemaError: {path.name}:line 1: YAML is unsupported; convert to JSONL, JSON or CSV")
        for number, record in entries:
            try:
                checked = validate_record(record, as_of)
                if checked["id"] in seen:
                    raise SchemaError(f"id: duplicate {checked['id']!r}")
                seen.add(checked["id"])
                records.append(checked)
            except SchemaError as exc:
                raise InputError(f"SchemaError: {path.name}:line {number}: {exc}") from None
        inputs.append({"file": path.name, "sha256": hashlib.sha256(raw).hexdigest(), "records": len(entries)})
    return {**aggregate(records, as_of), "inputs": inputs}


def atomic_write(path, text):
    path = Path(path)
    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n",
                                         dir=path.parent, prefix=".ars-tmp-", delete=False) as handle:
            temporary = Path(handle.name)
            handle.write(text)
        os.replace(temporary, path)
    except OSError as exc:
        raise InputError(f"WriteError: {path}: {exc}") from None
    finally:
        if temporary is not None and temporary.exists():
            temporary.unlink()


def read_state(path):
    path = Path(path)
    if not path.is_file():
        raise InputError(f"MissingResults: {path}: first run ars run --input <directory>")
    try:
        state = json_load(path.read_text(encoding="utf-8"), str(path))
        # Recompute aggregates so edited state cannot silently change counts.
        rebuilt = aggregate(state["records"], state["as_of"])
        if any(state.get(key) != value for key, value in rebuilt.items()):
            raise InputError(f"SchemaError: {path}:line 1: state aggregates disagree with records; rerun ars run")
        inputs = state["inputs"]
        if not isinstance(inputs, list) or any(not isinstance(s, dict) or set(s) != {"file", "sha256", "records"}
                or not isinstance(s["file"], str) or "\u2014" in s["file"]
                or not isinstance(s["sha256"], str) or len(s["sha256"]) != 64
                or type(s["records"]) is not int or s["records"] < 0 for s in inputs):
            raise ValueError("invalid source manifest")
        if sum(s["records"] for s in inputs) != rebuilt["totals"]["total"]:
            raise ValueError("source counts disagree")
        return {**rebuilt, "inputs": inputs}
    except (OSError, UnicodeError, KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, InputError):
            raise
        raise InputError(f"SchemaError: {path}:line 1: invalid results: {exc}") from None


def parser():
    p = argparse.ArgumentParser(prog="ars", description="Compute observed agent reliability by task type. Local files only.")
    subs = p.add_subparsers(dest="command", required=True)
    f = subs.add_parser("fixtures", help="Generate 200 labelled synthetic records", epilog="Example: ars fixtures --out demo")
    f.add_argument("--out", required=True)
    r = subs.add_parser("run", help="Validate and aggregate local input", epilog="Example: ars run --input demo --as-of 2026-09-30")
    r.add_argument("--input", required=True)
    r.add_argument("--as-of", default=DEFAULT_AS_OF, help=f"Explicit future-date cutoff, default {DEFAULT_AS_OF}; never reads system clock")
    r.add_argument("--state", default=".ars/results.json")
    for command, help_text, example in (
            ("report", "Render provenance and exact observed figures", "ars report --format md --out report.md"),
            ("rank", "Rank observed reliability, optionally for one task type", "ars rank --task-type coding"),
            ("failures", "List observed failures with task and agent", "ars failures --task-type research")):
        s = subs.add_parser(command, help=help_text, epilog=f"Example: {example}")
        s.add_argument("--state", default=".ars/results.json")
        s.add_argument("--format", choices=("md", "json"), default="md" if command == "report" else "json")
        s.add_argument("--out", help="Atomically write output to a local file")
        if command != "report":
            s.add_argument("--task-type", help="Exact task type filter")
    return p


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fixtures":
            target = Path(args.out)
            if target.exists():
                raise InputError(f"WriteError: {target}: fixture directory already exists; choose a new path")
            # Stage the complete directory, then rename; never leave partial fixtures.
            target.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(dir=target.parent, prefix=".ars-fixtures-") as stage:
                folder = Path(stage) / "fixture"
                folder.mkdir()
                for name, content in fixture_files().items():
                    (folder / name).write_text(content, encoding="utf-8", newline="\n")
                os.rename(folder, target)
            print("Generated 200 SYNTHETIC records with hand-computed expectations.")
            return 0
        if args.command == "run":
            from datetime import date
            try:
                if date.fromisoformat(args.as_of).isoformat() != args.as_of:
                    raise ValueError()
            except ValueError:
                raise InputError("SchemaError: as_of: expected ISO calendar date YYYY-MM-DD") from None
            result = load_inputs(args.input, args.as_of)
            atomic_write(args.state, render(result, "json"))
            print(banner(result))
            print(f"Processed {result['totals']['total']} records. Results: {args.state}".replace("\u2014", "[U+2014]"))
            return 0
        result = read_state(args.state)
        if args.command == "report":
            output = render(result, args.format)
        else:
            rows = rank_groups(result, args.task_type) if args.command == "rank" else [
                r for r in result["records"] if r["outcome"] == "failure" and
                (args.task_type is None or r["task_type"] == args.task_type)]
            payload = {"banner": banner(result), "scope": "Observed input outcomes only; no predictions or measured savings.", "rows": rows}
            output = json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n" if args.format == "json" else (
                banner(result) + "\n\nObserved input outcomes only; no predictions or measured savings.\n\n" +
                "\n".join("- " + json.dumps(row, sort_keys=True, ensure_ascii=False) for row in rows) + "\n")
        if args.out:
            atomic_write(args.out, output)
        else:
            sys.stdout.write(output)
        return 0
    except InputError as exc:
        print(str(exc).replace("\u2014", "[U+2014]"), file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"WriteError: {exc.filename}: {exc.strerror}".replace("\u2014", "[U+2014]"), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
