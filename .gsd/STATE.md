# GSD State

**Active Milestone:** M001 — Infrastructure + Phase 0
**Active Slice:** S02 (next)
**Phase:** execution
**Requirements Status:** 12 active · 1 validated (R001) · 3 deferred · 3 out of scope

## Milestone Registry
- 🔄 **M001:** Infrastructure + Phase 0
- ⬜ **M002:** Phase 1 Monoculture (120 games)
- ⬜ **M003:** Phase 2 Pairwise + Persona (185 games)
- ⬜ **M004:** Analysis + Writing

## M001 Slice Status

| Slice | Title | Status |
|---|---|---|
| S01 | LiteLLM + Environment Setup | ✅ COMPLETE |
| S02 | Trade Island Engine | ⬜ next |
| S03 | Prompt Templates + Tolerant Parser | ⬜ planned |
| S04 | Phase 0 Calibration (30 games) | ⬜ planned |
| S05 | OSF Pre-Registration | ⬜ planned |

## Recent Decisions
- D026: S02 Concordia re-evaluation eliminated (D023 already closed)
- D027: S03 depends on S02 JSONL schema lock before template authoring
- D028: DeepSeek R1 cost risk is low in Phase 0 (~$0.044 worst case); revisit at M002

## Blockers
- None

## Next Action
Execute S02: Trade Island Engine.
- Entry: `src/simulation/` — 6 modules (config, llm_router, agent, gm, game, logger)
- Entry script: `scripts/run_game.py`
- Smoke test gate: `python scripts/run_game.py --config mistral-mono --games 1` → 25 rounds, ≤$0.02
- Key constraint: D023 (custom loop, no Concordia entity system), D025 (checkpoint to `data/raw/{game_id}/checkpoint_r{N:02d}.json`)
- Install deps first: polars, pytest, statsmodels, scikit-learn, networkx, sentence-transformers, seaborn

## Cost Burned
- $0.0008 (connectivity testing, S01)
- Phase 0 budget remaining: ~$1.499
