# M001: RNE Engine + Phase 0 Calibration

**Status:** 🔄 Active
**Started:** 2026-03-15
**Target completion:** ~2026-04-05 (3 weeks from start)
**Design authority:** `.gsd/SIMULATION_DESIGN.md`

## Goal

Build the complete Study 1 (RNE) simulation stack and validate it with a 240-session Phase 0 calibration run, then OSF pre-register before any Study 1 production data is collected.

---

## Success Criteria

- `python scripts/run_rne.py --family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1` completes 35 rounds, writes valid JSONL to `data/study1/{session_id}/`, produces `summary.json` with M1 cooperation_rate ∈ [0.0, 1.0]
- Perturbation fires exactly once at round 20 in every session
- All 7 CFIM families route correctly through `call_llm()` (verified via mock tests)
- Phase 0: 240 sessions complete (4 families × 10 × 3 conditions × 2 disclosure); JSON parse rate ≥90% per family; ≥1 completed trade per session
- `data/phase0/calibration_report.md` documents go/no-go decision for Study 1
- OSF pre-registration submitted; URL in `data/metadata/osf_registration.json`
- `pytest tests/test_rne.py` passes all mock-mode tests (no API calls)
- Total cost ≤ $15 (infrastructure + Phase 0)

---

## Key Risks / Unknowns

- **RNE trade acceptance may be near-zero** — If LLMs don't produce compatible proposals, M1=0 for all sessions and behavioral variation cannot be measured. Retire in S01 (T02 smoke run) by verifying ≥1 completed trade in real 35-round session.
- **Prompt format sensitivity** — If compact prompts fail on Gemini or DeepSeek at >10%, must switch format. Retire in S03 (Phase 0) by measuring parse rate per family per condition.
- **Identity disclosure effect may not be detectable** — If |M6| is near zero for all pairs, H3 is null. Acceptable outcome (null = publishable); Phase 0 will give early signal.
- **Cost overrun on Gemini** — Gemini output tokens are $2.50/1M. 240 Phase 0 sessions × $0.015 = $3.60 Gemini alone. Monitor in S03 T01.

---

## Proof Strategy

- RNE trade acceptance → retire in S01 T02 by running real Mistral×Llama smoke session, verifying ≥1 `trade_result` event with `accepted=true`
- Prompt parse reliability → retire in S03 by measuring parse rate across 240 Phase 0 sessions per family
- Disclosure effect detectability → Phase 0 gives qualitative signal; formal test is Study 1 (M002)
- Cost overrun → track `total_cost_usd` in every `game_end` event; abort if any session >$0.05

---

## Verification Classes

- Contract verification: `pytest tests/test_rne.py -v` (mock-mode, no API) — all pass
- Integration verification: real Mistral×Llama smoke session (T03); 4-family Phase 0 run (S03)
- Operational verification: crash session mid-run, resume, verify no duplicate JSONL events and round counts are correct
- UAT / human verification: `data/phase0/calibration_report.md` reviewed by human for go/no-go before M002 starts

---

## Milestone Definition of Done

This milestone is complete only when all are true:

- [ ] S01–S04 all have `[x]` in the slices checklist below
- [ ] `pytest tests/test_rne.py` passes with 0 failures, 0 errors
- [ ] Real smoke run completed: `data/study1/*/game.jsonl` exists with 70 `round_end` events (35 rounds × 2 agents), 1 `perturbation` event, `summary.json` with valid M1
- [ ] Phase 0 calibration complete: 240 sessions, parse rate ≥90% per family, report written
- [ ] OSF registration submitted; URL recorded
- [ ] Total cost ≤ $15

---

## Requirement Coverage

- Covers: R001 ✅, R002, R003, R004 ✅, R005, R006, R007, R008, R009 (partial)
- Leaves for later: R010 (M002), R011 (M003), R012 (M004), R013 (M004)
- Orphan risks: none

---

## Slices

- [x] **S01: RNE Engine + LLM Router** `risk:high` `depends:[]`
  > After this: `python scripts/run_rne.py --family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1` completes 35 rounds, writes JSONL + summary.json; `pytest tests/test_rne.py` passes all mock-mode tests.

- [ ] **S02: RNE Prompt Architecture** `risk:medium` `depends:[S01]`
  > After this: all 3 framing variants and 2 disclosure variants produce correctly formatted LLM messages; identity disclosure injection tested; tolerant parser handles all 4 failure modes; `pytest tests/test_rne_prompts.py` passes.

- [ ] **S03: Phase 0 Calibration** `risk:medium` `depends:[S01,S02]`
  > After this: 240 Phase 0 sessions complete; parse rate ≥90% per family confirmed; `data/phase0/calibration_report.md` written with go/no-go for Study 1.

- [ ] **S04: OSF Pre-Registration** `risk:low` `depends:[S01]`
  > After this: OSF registration formally submitted; URL in `data/metadata/osf_registration.json`; analysis stubs H1–H5 pre-registration timestamp confirmed.

---

## Boundary Map

### S01 → S02

Produces:
- `src/simulation/rne_game.py` — `RNERunner.run_session(config, mock_response)` with full 35-round loop
- `data/study1/{session_id}/game.jsonl` schema — locked event names and fields
- `data/study1/{session_id}/summary.json` schema — M1–M4, session_id, family_a/b, condition, disclosure, framing, total_cost_usd
- `data/study1/{session_id}/metadata.json` schema — full RNEConfig dict + wall_clock_seconds
- `scripts/run_rne.py` — CLI entry point
- `pytest tests/test_rne.py` — all mock tests passing

Consumes:
- nothing (S01 is the base)

### S01 → S03

Produces:
- All of S01 → S02 above
- `RNEConfig` with validated family fields — Phase 0 runner uses this directly

Consumes:
- nothing

### S02 → S03

Produces:
- `src/prompts/rne_prompts.py` — `build_system_prompt()`, `build_round_messages(config, round_num, agent_id, inventory, history)` supporting all 3 framings + 2 disclosure variants
- `parse_rne_response(raw)` — tolerant parser returning structured dict or None

Consumes:
- JSONL event schema from S01 (prompt variable names must match schema field names)
- `RNEConfig` from S01

### S03 → S04

Produces:
- Phase 0 data in `data/phase0/` — 240 sessions, valid JSONL
- `data/phase0/calibration_report.md` — per-family parse rates, cooperation rates, cost totals, go/no-go

Consumes:
- S04 (OSF) can proceed in parallel with S03 — hard constraint is submission before M002 starts
