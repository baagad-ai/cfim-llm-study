# GSD State

**Active Milestone:** M001 — Infrastructure + Phase 0
**Active Slice:** S02 — Concordia v2.0 Integration + Trade Island
**Phase:** execution
**Requirements Status:** 12 active · 1 validated (R001) · 3 deferred · 3 out of scope

## Milestone Registry

- 🔄 **M001:** Infrastructure + Phase 0 (Setup + Calibration + 30 games)
- ⬜ **M002:** Phase 1 Monoculture (120 games)
- ⬜ **M003:** Phase 2 Pairwise + Persona + Validation (185 games)
- ⬜ **M004:** Analysis + Writing

## M001 Slice Status

| Slice | Status | Notes |
|---|---|---|
| S01 | ✅ COMPLETE | All 4 providers verified. See S01-SUMMARY.md |
| S02 | ⬜ next | Concordia eval + Trade Island engine |
| S03 | ⬜ planned | Prompt templates (after S02 schema confirmed) |
| S04 | ⬜ planned | Phase 0: 30 calibration games |
| S05 | ⬜ planned | OSF pre-registration (MUST complete before Phase 1) |

## Resolved Infrastructure Issues (S01)

All recorded in DECISIONS.md. These must be respected in S02+:

1. **DeepSeek**: use `openrouter/deepseek/deepseek-chat` + `OPENROUTER_API_KEY`
2. **Gemini**: every call needs `thinking={'type':'disabled','budget_tokens':0}` + `max_tokens=200`; NO `response_format`; strip fences before `json.loads()`
3. **Mistral**: pinned to `mistral-small-2506` (not 3.1-2503)
4. **Global**: `litellm.drop_params = True` always set

## Games Progress

| Phase | Completed | Target |
|---|---|---|
| Phase 0 | 0 | 30 |
| Phase 1 | 0 | 120 |
| Phase 2 | 0 | 150 |
| Phase 2B | 0 | 20 |
| Phase 2C | 0 | 15 |
| **Total** | **0** | **335** |

## Cost

| Item | Spent | Budget |
|---|---|---|
| Connectivity testing | $0.0008 | — |
| Phase 0 | $0.00 | $1.50 |
| Phase 1 | $0.00 | $6.00 |
| **Total burned** | **$0.0008** | **$80.00 cap** |

## Blockers

- None currently

## Recent Decisions

- D023: Custom game loop — Concordia entity system bypassed (sample_text interface incompatible with per-provider workarounds)
- D024: DeepSeek R1 for reflections via OpenRouter; V3.2 for all other DeepSeek calls
- D025: JSON per-round checkpoints (checkpoint_r{N:02d}.json), resume from last checkpoint

## Next Action

**S02, T01:** Install remaining dependency stack — `gdm-concordia` already installed from GitHub as 2.4.0. Remaining: `polars`, `statsmodels`, `scikit-learn`, `networkx`, `sentence-transformers`, `seaborn`, `matplotlib`, `pydantic`, `pytest`, `jupyter`. Then pin to requirements-lock.txt.
Then T02: Implement custom game loop (D023 — skip Concordia marketplace evaluation, go straight to implementation).

## Git History

```
b9c0ded  M001/S01 COMPLETE: all 4 providers verified
c4a9a1d  M001/S01: GSD init + project scaffold
dd3d0ce  init: add research blueprint v6
```

Branch: `main`
Remote: not yet pushed (GitHub repo creation is part of S05/T03)
