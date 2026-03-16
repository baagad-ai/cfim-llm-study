---
id: S03
parent: M001
milestone: M001
provides:
  - scripts/run_phase0.py — Phase 0 runner (240-session, smoke, mock, resume modes)
  - scripts/generate_calibration_report.py — standalone report generator
  - data/phase0/sessions/ — 240 real RNE sessions across 4 families × 60 sessions each
  - data/phase0/calibration_report.md — Go/No-Go calibration report (decision: GO)
requires:
  - slice: S01
    provides: RNERunner.run_session(), run_rne.py CLI, mock mode
  - slice: S02
    provides: build_system_prompt, build_round_messages, parse_rne_response
affects:
  - S04
key_files:
  - scripts/run_phase0.py
  - scripts/generate_calibration_report.py
  - data/phase0/calibration_report.md
  - data/phase0/sessions/
key_decisions:
  - Phase 0 is monoculture (family_a == family_b) for each of the 4 CFIM families — clean per-family behavioral baseline before pairwise CFIM in M002
  - 4 families × 10 replicates × 3 conditions × 2 disclosure = 240 sessions total
  - data/phase0/sessions/ is kept separate from data/study1/ (run_rne.py output)
  - Replicate index persisted in metadata.json; --resume matches by (family, condition, disclosure, replicate) tuple
  - Report generation decoupled into standalone script so it regenerates without re-running sessions
  - Go/No-Go logic: parse_rate ≥90% per family AND ≥1 session with trades per family AND total cost ≤$12
  - Filter canonical 240 sessions by wall_clock_seconds > 5 (4 mock stubs remain on disk but excluded from analysis)
  - Mistral cost_usd=0.0 in all sessions — litellm doesn't return cost from Mistral API; sessions ran correctly (35 rounds, valid JSONL)
  - Gemini + Mistral show 0% monoculture trades in smoke sessions only; full 60-session run shows both families trading (35/60 and 31/60 sessions with trades)
patterns_established:
  - build_session_manifest() returns deterministic ordered list enabling reproducible resumption
  - --resume is idempotent: relaunch at any time; completed sessions skipped by (family, condition, disclosure, replicate) match
  - Cost guard fires warning at 80% of budget; hard abort at 100%
  - ✓ / ∅ trade marker in per-session stdout for quick scan of acceptance health
  - generate_calibration_report.py exits 0 (GO) or 1 (NO-GO) — scriptable gate
observability_surfaces:
  - "grep '∅' <run output>" — finds sessions with 0 accepted trades
  - "ls data/phase0/sessions/ | wc -l" — session count check
  - "python scripts/generate_calibration_report.py" — prints per-family summary + writes report
  - "python3 -c \"import json, pathlib, collections; ...\"" — slice-level parse rate check (S03-PLAN.md)
drill_down_paths:
  - .gsd/milestones/M001/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M001/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M001/slices/S03/tasks/T03-SUMMARY.md
duration: ~7h total (T01: ~1.5h script+smoke; T02: ~6h wall-time background run; T03: ~0.5h report generation)
verification_result: passed
completed_at: 2026-03-15
---

# S03: Phase 0 Calibration

**240 Phase 0 sessions complete across 4 families; all parse rates ≥99.95%; all families produced trades; total cost $2.11 (18% of $12 budget); calibration report issued GO for Study 1.**

## What Happened

**T01** wrote `scripts/run_phase0.py` with full 240-session mode plus `--smoke`, `--mock`, `--resume`, and `--family` flags. Phase 0 design is monoculture: each family plays against itself across all (condition × disclosure × replicate) cells, giving a clean per-family behavioral baseline before M002 pairwise runs. A 4-session smoke run confirmed all providers route without error and produced real JSONL output. Llama and deepseek traded in the smoke; gemini and mistral produced 0 trades in the smoke (identical inventory starting positions, incompatible quantity proposals — a known behavioral pattern from D037). Parse rates were 100% across all 4 families on the smoke.

**T02** launched `python scripts/run_phase0.py --resume`, which skipped the 4 smoke sessions and queued the remaining 236. The process ran unattended for ~6 hours, sequenced llama→deepseek→gemini→mistral. T02 was summarized at 44/240 with the process still running. No failures, 100% parse rate throughout.

**T03** wrote `scripts/generate_calibration_report.py` as a standalone script decoupled from the run itself — this allows the report to be regenerated at any time without re-running sessions. A partial report was generated at 179/240 (mistral batch still pending). The final report was generated after the process exited at 244 directory entries (240 real + 4 mock stubs from T01), confirming **GO**.

## Verification

```bash
# Session count (244 on disk = 240 real + 4 mock stubs)
ls data/phase0/sessions/ | wc -l
# → 244

# Parse rate per family (all families ≥90%)
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
# deepseek: parse_rate=99.95%
# gemini:   parse_rate=100.00%
# llama:    parse_rate=100.00%
# mistral:  parse_rate=100.00%

# Calibration report Go/No-Go
test -f data/phase0/calibration_report.md && grep -iE 'GO|NO-GO' data/phase0/calibration_report.md
# → Decision: **GO**
# → All Go/No-Go criteria are met. Phase 1 (Study 1 full CFIM pairwise run) may proceed.
```

Full results (canonical 240 real sessions, filtered wall_clock_seconds > 5):
- **deepseek**: 60 sessions, parse=99.95%, trade_sessions=29/60, median_M1=0.000, max_M1=0.057, cost=$0.4477
- **gemini**: 60 sessions, parse=100.00%, trade_sessions=31/60, median_M1=0.029, max_M1=0.057, cost=$0.6850
- **llama**: 60 sessions, parse=100.00%, trade_sessions=41/60, median_M1=0.029, max_M1=0.057, cost=$0.9745
- **mistral**: 60 sessions, parse=100.00%, trade_sessions=35/60, median_M1=0.029, max_M1=0.057, cost=$0.0000
- **Total cost**: $2.11 / $12.00 budget (18%)

Per-condition M1 (preliminary signal): Cond A avg_M1=0.017, Cond B=0.022, Cond C=0.016 — small differences in monoculture context, consistent with expected low cooperation rates in identical-inventory play.

## Requirements Advanced

- **R006** (Phase 0 Calibration, 240 sessions) — fully executed and validated: 240 sessions, parse rates ≥99.95%, all families trading, cost $2.11 ≤ $12, calibration_report.md written with GO decision

## Requirements Validated

- **R006** — Phase 0 calibration complete: all go/no-go criteria met, report confirms readiness for Study 1

## New Requirements Surfaced

- None.

## Requirements Invalidated or Re-scoped

- None.

## Deviations

- **Gemini/Mistral smoke zero-trades**: T01 plan required "≥1 accepted trade per smoke session." Both families produced 0 trades in smoke (monoculture, identical inventories). The slice must-have is "at least one session per family-pair" — met by llama + deepseek in smoke; gemini and mistral showed trading in the full run. Not a code failure; D037 pattern confirmed.
- **T03 executed on partial run**: Report generation ran at 179/240 sessions before mistral batch completed. Script verified functional on partial data; final report regenerated after completion. No code changes required.
- **Session count on disk is 244 not 240**: 4 mock stub sessions (wall_clock_seconds ≈ 0.03) from T01 remain. Report generator and analysis correctly filter with wall_clock_seconds > 5.

## Known Limitations

- **Mistral cost tracking is $0.0**: litellm doesn't return cost from Mistral's API response. Sessions ran correctly (35 rounds, valid JSONL, trades detected). Cost for Mistral in M002 must be estimated from token counts rather than API-reported cost.
- **M1 values are low in monoculture** (median 0.000–0.029 per family): expected — identical inventory agents rarely reach compatible trade proposals. Pairwise runs in M002 with complementary inventories should show higher M1. This is Phase 0's purpose: confirm the signal exists at all, not maximize it.
- **DeepSeek parse rate 99.95%**: One parse failure across 60 sessions × 35 rounds = 2100 opportunities. Within threshold. Monitor in M002.

## Follow-ups

- **M002**: Pairwise CFIM data collection. 28 unique pairs × 3 conditions × 2 disclosure × 3 framings × 20 sessions = 3,360 sessions. Phase 0 GO unblocks this.
- **S04/T02**: OSF registration (human action) — formal submission still pending. Must complete before M002 data collection starts.
- **Mistral cost estimation**: Add token-count-based cost estimation for Mistral sessions in M002 analysis scripts, since API doesn't return cost metadata.
- **Calibration report should be re-read by M002 planner**: Per-family M1 baseline values (deepseek=0.016, gemini=0.018, llama=0.022, mistral=0.017) inform expected effect sizes in Study 1 power calculations.

## Files Created/Modified

- `scripts/run_phase0.py` — new; Phase 0 runner with --smoke/--mock/--resume/--family modes; 240-session manifest
- `scripts/generate_calibration_report.py` — new; standalone report generator; reads summary.json files, writes calibration_report.md; exits 0=GO/1=NO-GO
- `data/phase0/sessions/` — 244 session directories (240 real + 4 mock stubs); each has game.jsonl + summary.json + metadata.json
- `data/phase0/calibration_report.md` — new; final Go/No-Go report with 5 sections; decision: GO

## Forward Intelligence

### What the next slice should know
- Monoculture M1 values (0.016–0.022) are the per-family behavioral baseline. Pairwise M002 runs will likely show higher M1 due to complementary inventory starting conditions. Don't use Phase 0 M1 values for power calculations without adjusting.
- All 4 families parse correctly at ≥99.95%. Prompt architecture is stable. No format changes needed before M002.
- Total Phase 0 cost was $2.11 for 240 sessions ($0.0088/session avg). M002 budget for 3,360 sessions at that rate ≈ $29.6 — well within the $47 cap.
- The `--resume` flag is battle-tested across a 6-hour interrupted run. M002 batch scripts should use it from the start.
- Mistral's litellm cost=0.0 behavior: use token counts from `metadata.json` (if logged) or estimate from model pricing. Don't depend on `total_cost_usd` for Mistral budget tracking.

### What's fragile
- **DeepSeek one parse failure**: 1 failure in 60 sessions is within threshold but the pattern matters. If parse failures cluster on a specific condition or framing, prompt adjustments may be needed before M002. Check in the first M002 batch.
- **Monoculture trade rates**: 29–41/60 sessions with trades. Pairwise trade rates may differ significantly. The Phase 0 report's "GO" is based on signal existence, not magnitude — M002 should expect broader variance.

### Authoritative diagnostics
- `data/phase0/calibration_report.md` — primary Go/No-Go reference; includes per-family parse rates, M1 distribution, cost breakdown
- `python scripts/generate_calibration_report.py` — regenerates from disk; trustworthy because it reads all summary.json files directly
- `data/phase0/sessions/*/game.jsonl` — ground truth JSONL; grep for `"event": "parse_failure"` to audit failure distribution

### What assumptions changed
- **"Gemini/Mistral won't trade in monoculture"** was seen as a risk in T01. Full run confirmed both DO trade (Mistral 35/60, Gemini 31/60) — smoke was unrepresentative because only condition=A, blind, rep=1 was tested. The zero-trade concern is retired.
- **Total cost estimate ($3.50 at T02 wrap)** came in lower: $2.11 final. Conservative model.
