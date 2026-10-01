# Local acceptance evidence

Measured on 2026-10-01 with Python 3.12.10 and pytest 8.3.5 on this Windows CPU environment. No real trial data, model calls, GPU workloads or external service calls were used.

- `python -m pytest -q`: 42 tests passed. The tests compare exact planted totals, every agent/task group, task totals and failure IDs against independent hand-computed expectations.
- Installed the actual `ars` entry point using local editable installation with `--no-build-isolation --no-deps --no-index`.
- Timed `ars fixtures --out demo`, `ars run --input demo`, then `ars report --format md` in separate processes using a PowerShell Stopwatch: 0.7361772 seconds including Markdown rendering to console and a local capture file.
- A separate `ars report --format json --out .ars/demo-report.json` took 0.2035932 seconds, including process startup and atomic write.
- Computed synthetic totals: 200 attempts, 145 successes, 55 failures, exact fraction 29/40. All 55 planted recorded failures found and no additional failure IDs.
- Mutation test changes one success to failure and confirms that output changes. Determinism test repeats aggregation and Markdown/JSON writes and compares bytes.
- The hand-written five-record synthetic example yields 3 successes and 2 failures. Real input format tests use synthetic test construction with an explicit simulated Henry attestation, not actual Henry operating data.

These timings are local measurements of the synthetic fixture demo, not performance promises for arbitrary datasets. Local runtime reports and fixtures remain ignored build artifacts. The two-week real-use window has not occurred; no usage, revenue, time savings or business verdict is claimed.
