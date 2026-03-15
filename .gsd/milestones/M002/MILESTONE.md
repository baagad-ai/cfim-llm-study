# M002: Study 1 Full CFIM Data Collection

**Status:** ⬜ Queued
**Depends on:** M001 complete (Phase 0 go/no-go + OSF registration submitted)
**Target sessions:** 3,360 (28 pairs × 3 conditions × 2 disclosure × 3 framings × 20 sessions)
**Calendar estimate:** ~2 weeks of batch runs after M001
**Budget:** ~$47

## Goal

Collect the full CFIM dataset — 3,360 Study 1 sessions across all 28 unique family pairs, all conditions, both disclosure sub-conditions, and all 3 framings.

## Success Criteria

- All 28 unique pairs × 120 sessions (3 conditions × 2 disclosure × 3 framings × 20) complete
- JSON parse rate ≥90% per family (confirmed in Phase 0, monitored here)
- No family produces M1=0.0 in >50% of sessions (behavioral signal requirement)
- `data/study1/` contains valid JSONL + summary.json for every session
- Total cost ≤ $47

## Definition of Done

- [ ] All 3,360 sessions complete with valid JSONL + summary.json
- [ ] Per-session M1–M4 computed and in summary.json for every session
- [ ] `data/study1/cfim_dataset.parquet` built from all session summaries (Polars)
- [ ] Per-cell statistics computed (mean M1 ± 95% CI for all 28 pairs × 3 conditions)
- [ ] Quality check: ≥20 valid sessions per cell (no cell has <20 due to parse failures)
- [ ] Cost ≤ $47

## Slices

| Slice | Description | Pairs | Sessions | Status |
|---|---|---|---|---|
| S01 | Core 4 families (llama, deepseek, gemini, mistral) | 6 pairs | 720 | ⬜ planned |
| S02 | Extended 3 families (gpt4o-mini, qwen, phi4) vs core 4 | 12 pairs | 1,440 | ⬜ planned |
| S03 | Extended-vs-extended pairs | 3 pairs + diagonals | 1,200 | ⬜ planned |
| S04 | Data assembly + quality check | — | — | ⬜ planned |

## Run Order

Start with core-4 pairs (S01) — cheapest per-session and most well-tested. Quality-gate after first 20 sessions per pair before continuing. Add extended families in S02/S03.

## Quality Gate Per Cell

After first 5 sessions of any new family pair:
- Parse rate ≥90%?
- M1 > 0 in at least 2 of 5 sessions?
- `game_end` event present in all 5?
- Session cost ≤ $0.05?

If any gate fails → STOP, diagnose, do not continue that pair.

## Data Organization

```
data/study1/
  {session_id}/
    game.jsonl
    summary.json        ← M1–M4, config fields, total_cost_usd
    metadata.json       ← full RNEConfig + wall_clock_seconds
  cfim_dataset.parquet  ← assembled after all sessions complete (S04)
```

## Risks

1. **Gemini parse instability at scale** — 95% parse rate in Phase 0 may degrade at higher volume. Monitor per-cell parse rate; switch to verbose prompt if drops below 90%.
2. **Rate limits** — Groq has generous limits; Together.ai may rate-limit qwen/phi4 at high burst. Add 1s delay between sessions if 429s appear.
3. **Cost overrun** — Gemini at $0.015/session × 840 sessions = $12.60. Track cumulative cost; abort and report if approaching $47.
