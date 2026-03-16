# S03: Phase 0 Calibration — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: Phase 0 produces a structured calibration report with a binary Go/No-Go decision. The report is computed from real API session data (240 sessions, 4 families). Human review of the report and Go/No-Go decision is the required gate before Study 1 begins. No live UI or runtime service to verify.

## Preconditions

```bash
cd /Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family
source .venv/bin/activate
# Phase 0 run complete (244 dirs on disk, process exited)
ls data/phase0/sessions/ | wc -l   # → 244
```

## Smoke Test

```bash
source .venv/bin/activate
python scripts/generate_calibration_report.py
# → Decision: **GO** printed; report written to data/phase0/calibration_report.md
grep -iE '^\s*Decision:' data/phase0/calibration_report.md
# → Decision: **GO**
```

## Test Cases

### 1. Session count — 240 real sessions completed

```bash
python3 -c "
import json, pathlib
sessions = list(pathlib.Path('data/phase0/sessions').glob('*/summary.json'))
real = [s for s in sessions if json.loads((s.parent/'metadata.json').read_text()).get('wall_clock_seconds', 0) > 5]
print(f'Real sessions: {len(real)}')
assert len(real) == 240, f'Expected 240, got {len(real)}'
print('PASS')
"
```
**Expected:** `Real sessions: 240` / `PASS`

### 2. Parse rate ≥90% per family

```bash
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
    assert rate >= 0.90, f'{fam} parse rate below 90%'
print('ALL PASS')
"
```
**Expected:**
```
deepseek: parse_rate=99.95%
gemini:   parse_rate=100.00%
llama:    parse_rate=100.00%
mistral:  parse_rate=100.00%
ALL PASS
```

### 3. ≥1 session with trades per family

```bash
python3 -c "
import json, pathlib, collections
sessions = list(pathlib.Path('data/phase0/sessions').glob('*/summary.json'))
trade_sessions = collections.defaultdict(int)
for s in sessions:
    meta = json.loads((s.parent/'metadata.json').read_text())
    if meta.get('wall_clock_seconds', 0) < 5:
        continue
    d = json.loads(s.read_text())
    if d.get('cooperation_rate', 0) > 0:
        trade_sessions[d['family_a']] += 1
for fam in sorted(trade_sessions):
    print(f'{fam}: sessions_with_trades={trade_sessions[fam]}')
    assert trade_sessions[fam] >= 1, f'{fam} has 0 trade sessions'
print('ALL PASS')
"
```
**Expected:**
```
deepseek: sessions_with_trades=29
gemini:   sessions_with_trades=31
llama:    sessions_with_trades=41
mistral:  sessions_with_trades=35
ALL PASS
```

### 4. Total cost ≤ $12

```bash
python3 -c "
import json, pathlib
sessions = list(pathlib.Path('data/phase0/sessions').glob('*/summary.json'))
total = sum(json.loads(s.read_text()).get('total_cost_usd', 0) for s in sessions)
print(f'Total cost: \${total:.4f}')
assert total <= 12.0, f'Cost \${total:.2f} exceeds \$12 budget'
print('PASS')
"
```
**Expected:** `Total cost: $2.1132` / `PASS`

### 5. Calibration report exists with GO decision

```bash
test -f data/phase0/calibration_report.md && echo "FILE EXISTS" || echo "MISSING"
grep -iE '^\s*Decision:' data/phase0/calibration_report.md
grep -i "All Go/No-Go criteria are met" data/phase0/calibration_report.md
```
**Expected:**
```
FILE EXISTS
  Decision: **GO**
All Go/No-Go criteria are met. Phase 1 (Study 1 full CFIM pairwise run) may proceed.
```

### 6. Session file structure integrity

```bash
python3 -c "
import pathlib
failures = []
for sess_dir in sorted(pathlib.Path('data/phase0/sessions').iterdir()):
    for fname in ('game.jsonl', 'summary.json', 'metadata.json'):
        f = sess_dir / fname
        if not f.exists():
            failures.append(f'{sess_dir.name}/{fname} missing')
if failures:
    for f in failures[:5]:
        print('MISSING:', f)
    print(f'Total: {len(failures)} missing files')
else:
    print(f'All session dirs have 3 required files. PASS')
"
```
**Expected:** `All session dirs have 3 required files. PASS`

### 7. JSONL event integrity (spot check)

```bash
python3 -c "
import json, pathlib, collections
# Spot-check: verify round_end and perturbation counts in a few sessions per family
import random; random.seed(42)
sessions = list(pathlib.Path('data/phase0/sessions').glob('*/summary.json'))
real = [s for s in sessions if json.loads((s.parent/'metadata.json').read_text()).get('wall_clock_seconds', 0) > 5]
sample = random.sample(real, min(8, len(real)))
for s in sample:
    meta = json.loads((s.parent/'metadata.json').read_text())
    game = s.parent / 'game.jsonl'
    events = [json.loads(line)['event'] for line in game.read_text().strip().split('\n')]
    re_count = events.count('round_end')
    pert_count = events.count('perturbation')
    fam = json.loads(s.read_text())['family_a']
    ok = re_count == 70 and pert_count == 1
    print(f'{fam} {s.parent.name[:8]}: round_end={re_count} perturbation={pert_count} {\"OK\" if ok else \"FAIL\"}')
"
```
**Expected:** All lines show `round_end=70 perturbation=1 OK`

### 8. Mock mode runs without API calls

```bash
source .venv/bin/activate
python scripts/run_phase0.py --smoke --mock
# Exit code 0, no real API calls
echo "Exit: $?"
```
**Expected:** `Phase 0 smoke complete: 4 done...` / `Exit: 0`

### 9. Resume is idempotent (no double-counting)

```bash
source .venv/bin/activate
python scripts/run_phase0.py --resume
# All sessions already complete — should skip 240+ sessions and exit immediately
echo "Exit: $?"
```
**Expected:** `0 done, 240 skipped` (or similar) / `Exit: 0`

## Edge Cases

### Mock stubs excluded from analysis

```bash
python3 -c "
import json, pathlib
sessions = list(pathlib.Path('data/phase0/sessions').glob('*/summary.json'))
stubs = [s for s in sessions if json.loads((s.parent/'metadata.json').read_text()).get('wall_clock_seconds', 0) < 5]
print(f'Mock stubs on disk: {len(stubs)}')
print(f'Expected: 4 (from T01 smoke --mock run)')
"
```
**Expected:** `Mock stubs on disk: 4`

### Calibration report regeneration is idempotent

```bash
source .venv/bin/activate
python scripts/generate_calibration_report.py
python scripts/generate_calibration_report.py   # second run
grep -c 'GO' data/phase0/calibration_report.md  # count should be same both runs
```
**Expected:** Same GO decision on both runs; no duplicate content written.

## Failure Signals

- `Decision: **NO-GO**` in calibration_report.md — one or more families below 90% parse rate OR 0 trade sessions
- Any family parse_rate < 90% in the parse-rate check script
- `ls data/phase0/sessions/ | wc -l` < 244 — run didn't complete fully
- `game.jsonl` with round_end != 70 — engine ran wrong number of rounds
- `perturbation` count != 1 in game.jsonl — perturbation fired wrong

## Requirements Proved By This UAT

- **R006** (Phase 0 Calibration, 240 sessions) — 240 sessions verified, parse rates ≥99.95%, trades confirmed per family, cost $2.11 ≤ $12, GO decision issued

## Not Proven By This UAT

- **R006 cross-family trade rates**: Phase 0 is monoculture only. Pairwise (family_a ≠ family_b) trade rates are untested until M002.
- **M5 (minimum acceptable offer)**: Condition C sessions exist in Phase 0 data, but M5 computation is out of scope for Phase 0.
- **M6 (identity sensitivity)**: Cross-session metric computed at analysis stage (M004); requires pairwise data from M002.
- **Disclosure effect signal**: Preliminary per-condition M1 differences exist (Cond B slightly higher) but N=80/condition in monoculture is insufficient for formal inference. Confirmed in Study 1.

## Notes for Tester

- **Mistral cost shows $0.00**: This is a litellm/Mistral API limitation — cost metadata is not returned in the response. Sessions ran correctly. Do not interpret as free; estimate from token counts if budget tracking is needed.
- **244 dirs, not 240**: Four mock stubs from T01's `--smoke --mock` run remain on disk. They have `wall_clock_seconds ≈ 0.03` in metadata.json and are correctly excluded by the analysis scripts. You can delete them (`rm -rf data/phase0/sessions/{9bdfb9ca,08c5a773,bb3f3072,05583407}` approx — verify by checking `wall_clock_seconds < 5`) but it's not required.
- **Low M1 values are expected**: Monoculture sessions (same family playing itself) start with identical inventories, limiting trade opportunities. Median M1 of 0.000–0.029 is correct behavior, not a bug. Pairwise M002 sessions will have complementary inventories.
- **Go/No-Go requires human review**: The report flags GO on quantitative criteria, but a human should read Section 4 (Family-specific observations) in `data/phase0/calibration_report.md` before authorizing Study 1. Pay attention to the Mistral and DeepSeek notes.
- **S04 must complete before Study 1 begins**: OSF pre-registration (S04/T02) is a human action still pending. The Phase 0 GO does not authorize M002 until OSF registration is formally submitted.
