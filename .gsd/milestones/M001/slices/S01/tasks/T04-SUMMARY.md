---
id: T04
parent: S01
milestone: M001
provides:
  - scripts/run_rne.py CLI (argparse, --family-a/b, --condition, --disclosure, --framing, --games)
  - Real Mistral×Llama smoke run: session 3230fd13, 35 rounds, 1 accepted trade, cost $0.007
key_files:
  - scripts/run_rne.py
  - data/study1/3230fd13/summary.json
key_decisions:
  - run_rne.py writes sessions to data/study1/{session_id}/ (not data/raw/)
  - CLI accepts --games N to run multiple sessions sequentially
patterns_established:
  - Session output: game.jsonl + metadata.json + summary.json in data/study1/{session_id}/
observability_surfaces:
  - summary.json per session: cooperation_rate, total_cost_usd, parse_failure_count
  - game.jsonl: full round-level event trace for audit
duration: ~45m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T04: run_rne.py CLI + smoke run

**`scripts/run_rne.py` CLI ships; real Mistral×Llama smoke session (3230fd13) completes 35 rounds with 1 accepted trade at $0.007.**

## What Happened

Built `scripts/run_rne.py` CLI wiring `RNERunner` to argparse. Ran real smoke session:
- `--family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1`
- Session 3230fd13: 35 rounds completed, M1=0.0286 (1 accepted trade), exploitation_delta=1.0, cost=$0.007205, parse_failure_count=0.

S01 slice-level verification passed. 165 mock-mode tests pass.

## Verification

```
python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1

Session 3230fd13:
  cooperation_rate:    0.0286  (1/35 rounds)
  total_cost_usd:      0.00721
  parse_failure_count: 0
  total_rounds:        35
  completed_trades:    1  ✓ (≥1 required)

pytest tests/test_rne.py tests/test_rne_prompts.py -q
→ 165 passed, 1 warning
```

## Diagnostics

- `data/study1/{session_id}/summary.json` — M1–M4, cost, parse failures
- `data/study1/{session_id}/game.jsonl` — full round-level event trace
- `data/study1/{session_id}/metadata.json` — session config (families, condition, disclosure, framing, seed)

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `scripts/run_rne.py` — CLI entry point for Study 1 sessions
- `data/study1/3230fd13/` — smoke run session output (game.jsonl, metadata.json, summary.json)
