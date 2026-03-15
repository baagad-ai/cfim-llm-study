# M002: Phase 1 — Monoculture (120 Games)

**Status:** ⬜ Queued
**Depends on:** M001 complete + OSF pre-registered
**Target:** 120 games, 4 families × 30 games
**Calendar estimate:** Weeks 3-4 (8-10 days at 15/day)
**Budget:** ~$6.00

## Goal

Establish baseline behavioral signatures for each model family in monoculture (same-family) conditions. This is the reference point for all pairwise comparisons.

## Definition of Done

- [ ] 30 games per family (Llama, DeepSeek, Gemini, Mistral) with valid JSONL logs
- [ ] Resource specialty assignments recorded as covariates for all 120 games
- [ ] Intermediate quality check after 15 games per model (catch systematic failures early)
- [ ] Cost ≤ $6.00
- [ ] Polars dataframe built from all 120 game logs (Phase 1 dataset)
- [ ] Phase 1 descriptive statistics computed (per-family: Gini mean, VP mean, trade acceptance rate mean)
- [ ] No model produces degenerate behavior (all-wait, all-hoard) in >20% of games

## Slices

| Slice | Description | Status |
|---|---|---|
| S01 | Llama 3.3 70B — 30 monoculture games | ⬜ planned |
| S02 | DeepSeek V3.2 — 30 monoculture games | ⬜ planned |
| S03 | Gemini 2.5 Flash — 30 monoculture games | ⬜ planned |
| S04 | Mistral Small 3.1 — 30 monoculture games | ⬜ planned |

## Run Order

Run in order: Mistral (cheapest, catches any remaining bugs) → Llama → DeepSeek → Gemini (most expensive output tokens).

## Quality Gates Per Slice

After first 5 games of any slice:
- JSON parse rate ≥ 90%?
- Trade acceptance rate > 5%?
- ≥1 building action per game?
- Cost within expected range?

If any gate fails → STOP, diagnose, fix before continuing.

## Data Organization

```
data/phase1/
  llama/
    game_001.jsonl ... game_030.jsonl
  deepseek/
    game_001.jsonl ... game_030.jsonl
  gemini/
    game_001.jsonl ... game_030.jsonl
  mistral/
    game_001.jsonl ... game_030.jsonl
  phase1_dataset.parquet   # merged Polars dataframe
  PHASE1_DESCRIPTIVES.md   # summary statistics
```

## Risks

1. **Gemini output token costs**: at $2.50/1M output tokens, 30 games × $0.099/game = $2.97 just for Gemini. Monitor closely.
2. **API rate limits**: Groq has generous limits; DeepSeek and Mistral may have lower tier limits. Monitor 429 errors.
3. **Behavioral degeneration**: if a model family consistently fails to trade, the monoculture data will be uninteresting. Flag and consider prompt adjustment (document in DECISIONS.md).
