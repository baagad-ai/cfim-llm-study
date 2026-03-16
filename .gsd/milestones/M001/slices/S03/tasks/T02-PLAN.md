# T02: Full 240-session run

**Goal:** Execute the complete Phase 0 calibration — 240 RNE sessions (4 families × 10 replicates × 3 conditions × 2 disclosure) — using `python scripts/run_phase0.py --resume`.

## Inputs
- `scripts/run_phase0.py` (from T01) — already tested with 4-session smoke
- 8 existing sessions in `data/phase0/sessions/` (all `(family, A, blind, replicate=1)`) — will be auto-skipped by `--resume`

## Steps

- [ ] **T02.1** Launch full run with `--resume` flag (background process)
- [ ] **T02.2** Monitor cost vs. $12 budget mid-run; abort if approaching limit
- [ ] **T02.3** Verify session count = 240 on completion
- [ ] **T02.4** Verify parse rate ≥90% per family
- [ ] **T02.5** Confirm exit code 0 and no failed sessions

## Must-Haves

- 240 sessions total (already-complete sessions counted, new ones filling the rest)
- All families ≥90% parse rate
- Total cost ≤$12

## Estimated Wall Time

~3-5 hours (236 new sessions × ~87s/session average = ~5.7h; Llama sessions are faster ~51s)

## Cost Estimate

- llama: 60 sessions × ~$0.015 = ~$0.90
- deepseek: 60 sessions × ~$0.007 = ~$0.42
- gemini: 60 sessions × ~$0.011 = ~$0.66
- mistral: 60 sessions × ~$0.000 = ~$0.00
- Total estimate: ~$2.00 (well within $12 budget)
