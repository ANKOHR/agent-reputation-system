import json
import subprocess
import sys
import time
import pytest
from agent_reputation_system.cli import main
from agent_reputation_system.fixtures import fixture_records


def prepare(tmp_path):
    state = tmp_path / "state.json"
    data = tmp_path / "data"
    assert main(["fixtures", "--out", str(data)]) == 0
    assert main(["run", "--state", str(state), "--input", str(data)]) == 0
    return state, data


def test_run_completes_on_fixture(tmp_path, capsys):
    start = time.perf_counter()
    state, data = prepare(tmp_path)
    assert main(["report", "--state", str(state)]) == 0
    assert time.perf_counter() - start < 5
    assert "200 synthetic fixture records" in capsys.readouterr().out


def test_empty_input_renders_without_traceback(tmp_path, capsys):
    data = tmp_path / "empty"
    data.mkdir()
    state = tmp_path / "state.json"
    assert main(["run", "--state", str(state), "--input", str(data)]) == 0
    assert main(["report", "--state", str(state)]) == 0
    assert "Records: 0" in capsys.readouterr().out


def test_malformed_input_named_error(tmp_path, capsys):
    file = tmp_path / "bad.jsonl"
    file.write_text('# comment\n{"id":\n', encoding="utf-8")
    assert main(["run", "--input", str(tmp_path)]) == 2
    error = capsys.readouterr().err
    assert "ParseError" in error and "bad.jsonl" in error and "line 2" in error
    assert "Traceback" not in error


@pytest.mark.parametrize("suffix", ["json", "csv", "yaml"])
def test_unsupported_format_named_error(tmp_path, capsys, suffix):
    (tmp_path / f"bad.{suffix}").write_text("invalid content")
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert f"bad.{suffix}" in capsys.readouterr().err


def test_determinism_byte_identical(tmp_path):
    state, data = prepare(tmp_path)
    first = state.read_bytes()
    assert main(["run", "--state", str(state), "--input", str(data)]) == 0
    assert first == state.read_bytes()
    for format in ("md", "json"):
        out = tmp_path / f"report.{format}"
        args = ["report", "--state", str(state), "--format", format, "--out", str(out)]
        assert main(args) == 0
        first = out.read_bytes()
        assert main(args) == 0
        assert out.read_bytes() == first


def test_cli_smoke_all_subcommands(tmp_path, capsys):
    state, _ = prepare(tmp_path)
    for cmd in (["report", "--format", "json"], ["rank", "--task-type", "coding"], ["failures"]):
        assert main([*cmd, "--state", str(state)]) == 0
    capsys.readouterr()
    for cmd in ("fixtures", "run", "report", "rank", "failures"):
        with pytest.raises(SystemExit) as exc:
            main([cmd, "--help"])
        assert exc.value.code == 0
        output = capsys.readouterr().out
        assert "Example:" in output and "\u2014" not in output


def test_missing_input_named_error(tmp_path, capsys):
    assert main(["run", "--input", str(tmp_path / "missing")]) == 2
    assert "MissingInput" in capsys.readouterr().err


def test_report_write_failure_no_partial_files(tmp_path, capsys):
    state, _ = prepare(tmp_path)
    destination = tmp_path / "directory"
    destination.mkdir()
    before = set(tmp_path.iterdir())
    assert main(["report", "--state", str(state), "--out", str(destination)]) == 2
    assert "WriteError" in capsys.readouterr().err
    assert set(tmp_path.iterdir()) == before


def test_five_handwritten_observations(tmp_path):
    from pathlib import Path
    source = Path(__file__).parents[1] / "examples" / "five-records"
    state = tmp_path / "state.json"
    assert main(["run", "--state", str(state), "--input", str(source)]) == 0
    assert json.loads(state.read_text())["totals"] == {
        "total": 5, "successes": 3, "failures": 2, "success_rate_exact": "3/5"}


def test_process_entrypoint():
    result = subprocess.run([sys.executable, "-m", "agent_reputation_system.cli", "--help"],
                            capture_output=True, text=True)
    assert result.returncode == 0 and "fixtures" in result.stdout


def test_bad_run_preserves_previous_snapshot(tmp_path):
    state, data = prepare(tmp_path)
    before = state.read_bytes()
    (data / "bad.jsonl").write_text("{bad}")
    assert main(["run", "--state", str(state), "--input", str(data)]) == 2
    assert state.read_bytes() == before


@pytest.mark.parametrize("format", ["json", "csv", "jsonl"])
def test_real_input_formats_and_unicode(tmp_path, capsys, format):
    import csv
    row = fixture_records()[0]
    row.update(synthetic=False, entered_by="Henry", agent="亨利 café " + "x" * 3000,
               task_type=r"C:\Users\henry\任务")
    source = tmp_path / "input"
    source.mkdir()
    file = source / f"real.{format}"
    if format == "csv":
        with file.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            writer.writerow({**row, "synthetic": "false"})
    else:
        file.write_text(json.dumps([row] if format == "json" else row, ensure_ascii=False), encoding="utf-8")
    state = tmp_path / "state.json"
    assert main(["run", "--input", str(source), "--state", str(state)]) == 0
    assert main(["report", "--state", str(state), "--format", "json"]) == 0
    output = capsys.readouterr().out
    assert "1 real records attested as entered by Henry" in output
    assert row["agent"] in output


def test_tampered_snapshot_rejected(tmp_path, capsys):
    state, _ = prepare(tmp_path)
    result = json.loads(state.read_text(encoding="utf-8"))
    result["totals"]["successes"] = 200
    state.write_text(json.dumps(result), encoding="utf-8")
    assert main(["report", "--state", str(state)]) == 2
    assert "aggregates disagree" in capsys.readouterr().err


@pytest.mark.parametrize("content", ['{"id":"a","id":"b"}', '{"id":NaN}'])
def test_ambiguous_json_rejected(tmp_path, capsys, content):
    (tmp_path / "bad.jsonl").write_text(content)
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "ParseError" in capsys.readouterr().err


def test_fixture_existing_directory_preserved(tmp_path, capsys):
    sentinel = tmp_path / "keep.txt"
    sentinel.write_text("keep")
    assert main(["fixtures", "--out", str(tmp_path)]) == 2
    assert sentinel.read_text() == "keep"
    assert "WriteError" in capsys.readouterr().err


def test_invalid_utf8_named_error(tmp_path, capsys):
    (tmp_path / "bad.jsonl").write_bytes(b"\xff")
    assert main(["run", "--input", str(tmp_path)]) == 2
    assert "ParseError" in capsys.readouterr().err
