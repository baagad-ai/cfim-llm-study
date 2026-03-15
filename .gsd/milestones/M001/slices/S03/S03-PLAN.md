# S03: Phase 0 Calibration

**Goal:** Run 240 Phase 0 sessions across 4 families × 10 sessions × 3 conditions × 2 disclosure to validate prompt format, trade acceptance rate ≥10%, JSON parse rate ≥90% per family, and produce a Go/No-Go report for Phase 1 (Study 1 full CFIM).
**Demo:** `python scripts/run_phase0.py` completes all 240 sessions; `data/phase0/calibration_report.md` exists with Go/No-Go decision; total cost ≤$12.

## Must-Haves

- `scripts/run_phase0.py` — runs 4 families × 10 sessions × 3 conditions × 2 disclosure = 240 sessions
- JSON parse rate ≥90% per family confirmed
- ≥1 completed trade per session (M1>0 in at least one session per family-pair)
- `data/phase0/calibration_report.md` with: per-family parse rates, M1 distribution, cost totals, Go/No-Go recommendation
- Total Phase 0 cost ≤ $12

## Proof Level

- Operational — real API calls, real data produced
- Human/UAT required: yes — Phase 0 Go/No-Go requires human review before Phase 1 begins

## Verification

```bash
source .venv/bin/activate

python scripts/run_phase0.py

# Session count
ls data/phase0/sessions/ | wc -l
# → 240

# Parse rate check (per family)
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
# → All families ≥90%

test -f data/phase0/calibration_report.md && grep -iE 'GO|NO-GO' data/phase0/calibration_report.md
```

## Tasks

- [ ] **T01: run_phase0.py + 4-family test run** `est:1h`
  > Write `scripts/run_phase0.py` CLI. Run a 4-session smoke (1 per family) to confirm all providers route correctly. Verify ≥1 accepted trade per smoke session.

- [ ] **T02: Full 240-session run** `est:30m (wall time)`
  > Run all 240 Phase 0 sessions. Monitor cost per batch. Target total ≤$12.

- [ ] **T03: Calibration report** `est:45m`
  > Extract metrics. Write `data/phase0/calibration_report.md` with 5 sections: (1) Parse Rates, (2) Trade Acceptance (M1 distribution), (3) Cost Breakdown, (4) Family-specific observations, (5) Go/No-Go Decision.

## Files Likely Touched

- `scripts/run_phase0.py` — new
- `data/phase0/calibration_report.md` — new
- `data/phase0/sessions/` — session output dirs
