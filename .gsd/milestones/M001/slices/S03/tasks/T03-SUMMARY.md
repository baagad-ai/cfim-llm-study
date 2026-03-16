---
id: T03
parent: S03
milestone: M001
provides:
  - scripts/generate_calibration_report.py — report generator (reads all summary.json, writes calibration_report.md)
  - data/phase0/calibration_report.md — partial report (179/240 sessions at write time; regenerate when run completes)
key_files:
  - scripts/generate_calibration_report.py
  - data/phase0/calibration_report.md
key_decisions:
  - Report generation decoupled into standalone script so it can be re-run at any time without re-running sessions
  - Go/No-Go logic: parse_rate ≥90% per family AND ≥1 session with trades per family AND total cost ≤$12
patterns_established:
  - "python scripts/generate_calibration_report.py" regenerates report from any partial/complete session set
  - Report idempotent: safe to regenerate repeatedly as sessions accumulate
observability_surfaces:
  - "python scripts/generate_calibration_report.py" prints per-family summary to stdout and writes full markdown
  - Exit code 0 = GO, 1 = NO-GO
duration: ~4h wall (blocked on 240-session run completing)
verification_result: partial — run at 179/240, report generated and script verified functional
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Calibration Report

**`scripts/generate_calibration_report.py` written and verified; partial report generated at 179/240 sessions; full run still in progress (PID 79560), mistral batch not yet reached.**

## What Happened

The background run (PID 79560, bg-id c2cb4d05) from T02 is still executing — 179/240 sessions complete when this summary was written. The run is sequenced by family: llama (60 sessions) → deepseek (60) → gemini (60) → mistral (60). At write time: llama=61, deepseek=61, gemini=55 complete; mistral=2 (only the original smoke sessions).

`scripts/generate_calibration_report.py` was written and tested. It:
- Reads all `data/phase0/sessions/*/summary.json` files
- Computes per-family parse rates, M1 distribution, cost breakdown, per-condition M1 table
- Writes `data/phase0/calibration_report.md` with 5 sections
- Exits 0 (GO) or 1 (NO-GO); prints per-family summary to stdout

Partial-run report at 179/240 shows:
- deepseek: parse=100% trades=29/61 ✓
- gemini: parse=100% trades=26/55 ✓
- llama: parse=100% trades=41/61 ✓
- mistral: parse=100% (2 sessions only — incomplete) — trades=0/2 → NO-GO pending
- Total cost so far: $2.06 / $12.00 budget ✓

Current decision is NO-GO only because mistral hasn't run its full 60 sessions yet. The 3 complete families all pass both criteria.

## Verification

```bash
# Run completed at 179/240 (bg process still running as of summary write)
ls data/phase0/sessions/ | wc -l  # → 179+

# Script smoke-tested on partial data
python scripts/generate_calibration_report.py
# → report written, per-family summary printed, exit 1 (partial/NO-GO expected)

# Parse rates already passing for 3/4 families
python3 -c "
import json, pathlib, collections
sessions = list(pathlib.Path('data/phase0/sessions').glob('*/summary.json'))
parse_fails = collections.defaultdict(int)
totals = collections.defaultdict(int)
for s in sessions:
    d = json.loads(s.read_text())
    for fam in (d['family_a'], d['family_b']):
        totals[fam] += 1
        parse_fails[fam] += d.get('parse_failure_count', 0)
for fam in sorted(totals):
    rate = 1.0 - parse_fails[fam] / max(totals[fam] * 35, 1)
    print(f'{fam}: parse_rate={rate:.2%}')
"
# deepseek: 100.00%  gemini: 100.00%  llama: 100.00%  mistral: 100.00% (2 sessions)
```

## Diagnostics

```bash
# Check run progress
ls data/phase0/sessions/ | wc -l

# Check if run still alive
ps aux | grep run_phase0 | grep -v grep

# Relaunch if stopped before 240
source .venv/bin/activate && python scripts/run_phase0.py --resume

# Regenerate report when run completes
source .venv/bin/activate && python scripts/generate_calibration_report.py

# Full slice verification (S03 gate)
source .venv/bin/activate
ls data/phase0/sessions/ | wc -l                  # → 240
python scripts/generate_calibration_report.py     # → GO + all families pass
test -f data/phase0/calibration_report.md && grep -iE 'GO|NO-GO' data/phase0/calibration_report.md
```

## Deviations

- T03 execution overlapped with T02's still-running background process. Report generation was decoupled into a standalone script (not embedded in run_phase0.py) to keep concerns separate and allow regeneration without re-running sessions.

## Known Issues

- Run was at 179/240 (mistral batch pending) when this task's context timed out. The background process (PID 79560) is still running. T03 is structurally complete (script written, report generated) but **the final Go/No-Go decision requires regenerating the report after 240/240 sessions complete**.
- Resume path: wait for PID 79560 to finish (or `python scripts/run_phase0.py --resume` if it died), then `python scripts/generate_calibration_report.py`. Slice S03 verification checks should then all pass.

## Files Created/Modified

- `scripts/generate_calibration_report.py` — new; standalone report generator; reads summary.json files, writes calibration_report.md
- `data/phase0/calibration_report.md` — new; partial report (179/240 sessions); regenerate after full run
