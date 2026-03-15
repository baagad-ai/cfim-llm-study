# GSD State

**Active Milestone:** M001 — RNE Engine + Phase 0 Calibration
**Active Slice:** S01 — RNE Engine + LLM Router
**Active Task:** T02 — RNE Game Engine (next)
**Phase:** executing
**Slice Branch:** gsd/M001/S01
**Last Updated:** 2026-03-15

**Requirements Status:** 13 active · 2 validated · 3 deferred · 3 out of scope

---

## Milestone Registry

- 🔄 **M001:** RNE Engine + Phase 0 Calibration
- ⬜ **M002:** Study 1 Full CFIM Data Collection (3,360 sessions)
- ⬜ **M003:** Study 2 Harbour + Final Analysis
- ⬜ **M004:** Paper + Open-Source Release

---

## M001 Slice Status

| Slice | Title | Status | Notes |
|---|---|---|---|
| S01 | RNE Engine + LLM Router | 🔄 T01 ✅ · T02 next | T01 done: config/logger/router + 31 tests |
| S02 | RNE Prompt Architecture | ⬜ | Starts after S01 |
| S03 | Phase 0 Calibration | ⬜ | 240 sessions, starts after S01+S02 |
| S04 | OSF Pre-Registration | ⬜ | Can run parallel with S03; submission pending |

---

## Recent Decisions

- D041 — `call_llm(family)` + `call_llm_provider` split (RNE vs Trade Island)
- D042 — `RNEConfig` disclosure/framing defaults (blind/neutral)
- D047 — Gemini `response_format=json_object` re-enabled (D021 superseded)
- D056 — Analysis stubs H1–H5 replaced to match CFIM/RNE design
- D057 — H3 uses |M6| absolute value (two-sided disclosure effect)

---

## Blockers

- None

---

## Next Action

Execute **T02: RNE Game Engine** — write `src/simulation/rne_game.py`:
- `RNERunner.run_session(config, mock_response=None) -> dict`
- 35-round loop: simultaneous proposals → compatibility → respond → settlement → 10% decay → round_end
- Perturbation at round 20 (switch opponent strategy)
- M1–M4 computation post-game
- `summary.json` + `metadata.json`
- Inline `__main__` smoke test: `python src/simulation/rne_game.py` prints "smoke: ok"

Plan: `.gsd/milestones/M001/slices/S01/tasks/T02-PLAN.md`
