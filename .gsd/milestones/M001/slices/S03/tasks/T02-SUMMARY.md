---
id: T02
parent: S03
milestone: M001
provides:
  - data/phase0/sessions/ — Phase 0 run in progress; 44 sessions written at summary time; background process running unattended to completion (~240 sessions)
key_files:
  - scripts/run_phase0.py
  - data/phase0/sessions/
key_decisions:
  - Run launched with --resume; 4 real smoke sessions (family, A, blind, rep=1) auto-skipped; 236 new sessions queued
  - Background process id=c2cb4d05 continues unattended; safe to leave or re-launch with --resume
  - Session count on disk will be ~244 (240 + 4 mock stubs from T01); T03 must filter by wall_clock_seconds > 5 to get canonical 240
patterns_established:
  - "--resume is idempotent: relaunch at any time with `python scripts/run_phase0.py --resume`"
observability_surfaces:
  - "ls data/phase0/sessions/ | wc -l — check count (target 240+ when done)"
  - "bg_shell id=c2cb4d05 -- live output; scan for FAILED or BUDGET EXCEEDED"
duration: ~5-6h wall time (background); summary written at 44/240
verification_result: in-progress
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Full 240-session run

**`python scripts/run_phase0.py --resume` launched; 44/240 sessions complete, 0 failures, 100% parse rate, $0.60 cost — run proceeding unattended to completion.**

## What Happened

Launched full 240-session Phase 0 run with `--resume`. The process detected 4 already-complete smoke sessions and skipped them, then began executing the remaining 236 sessions sequentially (llama→deepseek→gemini→mistral, A→B→C, blind→disclosed, rep 1→10).

At summary write time (~32 min elapsed):
- **44 sessions** on disk, process at [37/240] llama cond=B disc=disclosed
- **100% parse rate** across all families, 0 parse failures
- **0 failed sessions**
- Cost: ~$0.60 projected to ~$3.50 total (29% of $12 budget)
- Llama trading consistently (1-2 trades/35 rounds per session); pattern healthy

The process runs unattended. It writes `summary.json` atomically per session — safe to interrupt and resume at any time.

## Completion Check (run after process exits)

```bash
source .venv/bin/activate

# 1. Session count (expect 240+ on disk; 4 mock stubs inflate count)
ls data/phase0/sessions/ | wc -l

# 2. Parse rate per family (all must be ≥90%)
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
```

## Resume / Recovery

If the process was interrupted (check `bg_shell output id=c2cb4d05`):
```bash
source .venv/bin/activate
python scripts/run_phase0.py --resume   # skips all completed sessions
```

## Known Issues

- **Session dir count ~244 not 240**: 4 mock stub sessions (wall_clock_seconds≈0.03) from T01 remain on disk. T03 calibration report should filter with `meta['wall_clock_seconds'] > 5` to get canonical 240.
- **Gemini/Mistral 0% monoculture trade rate**: expected (per D037, identical inventory agents don't trade). Parse rate unaffected.

## Files Created/Modified

- `.gsd/milestones/M001/slices/S03/tasks/T02-PLAN.md` — created
- `.gsd/milestones/M001/slices/S03/tasks/T02-SUMMARY.md` — this file
- `data/phase0/sessions/` — 44 new sessions at wrap time; growing to ~244 total
