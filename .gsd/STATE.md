# GSD State

**Active Milestone:** M001 — RNE Engine + Phase 0 Calibration
**Active Slice:** S05 — Study 2 Engine (Harbour v2)
**Phase:** executing
**Last updated:** 2026-03-16

## Progress

### M001 Slices
- ✅ **S01:** RNE Engine + LLM Router — COMPLETE (T01–T04 all done)
- ✅ **S02:** RNE Prompt Architecture — COMPLETE (T01–T03 all done)
- ✅ **S03:** Phase 0 Calibration — COMPLETE (244 sessions, GO decision)
- ✅ **S04:** OSF Pre-Registration — COMPLETE (https://osf.io/9354h)
- 🔄 **S05:** Study 2 Engine (Harbour v2) — NOT STARTED ← **NEXT**
- ~~S07:~~ DEPRECATED (duplicate of S04, do not execute)

### Key Artifacts
- GitHub: https://github.com/baagad-ai/cfim-llm-study
- OSF registration: https://osf.io/9354h (H1–H5 locked, pre-data)
- Pre-reg commit: ca3b54426f70fd7554ae11d7f51927d85b61c95c
- Phase 0 report: `data/phase0/calibration_report.md` — GO
- Tests: 165 passed (test_rne.py + test_rne_prompts.py), 189 passed (full suite)

## Milestone Registry
- 🔄 **M001:** RNE Engine + Phase 0 Calibration (1 slice remaining: S05)
- ⬜ **M002:** Study 1 Full CFIM Run (3,360 sessions) — starts after M001/S05
- ⬜ **M003:** Study 2 Harbour Games (~200 sessions)
- ⬜ **M004:** Analysis + Paper

## Next Action
Execute S05/T01: GameConfig v2 + GameState dataclass.
Design doc: `docs/plans/2026-03-15-simulation-engine-v2-design.md`
Key decisions: D048–D055 in `.gsd/DECISIONS.md`

## Blockers
None.

## Recent Decisions
- D048–D055: Harbour v2 engine design (broadcast+match, spoilage, destitution, RoundMetrics)
- D056: Analysis stubs H1–H5 replaced to match CFIM/RNE design (locked by OSF pre-registration)
