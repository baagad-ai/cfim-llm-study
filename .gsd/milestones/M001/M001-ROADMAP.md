# M001: Infrastructure + Phase 0

**Vision:** Complete simulation stack validated with 30 calibration games, OSF pre-registered, ready to begin Phase 1 production runs.

---

## Success Criteria

- `python scripts/run_game.py --config mistral-mono --games 1` completes 25 rounds, writes valid JSONL, costs ≤$0.02
- `python scripts/run_game.py --config phase0 --games 30` completes all 30 calibration games, total cost $0.00–$1.50
- All 4 model families (Llama, DeepSeek, Gemini, Mistral) participate in a single pairwise game; per-agent LLM routing verified by inspecting JSONL `model` fields
- Crash-resume tested: kill mid-game, resume from checkpoint, correct round continuation with no duplicate JSONL events
- OSF pre-registration confirmation URL recorded in `data/metadata/osf_registration.json`
- `requirements-lock.txt` committed with all exact pinned versions

---

## Key Risks / Unknowns

- **Game mechanics correctness** — Trade Island has a double-spending race condition across simultaneous proposals. GM resolution must validate trades sequentially against post-prior-trade inventory, not start-of-round snapshot. If this is wrong, experiments produce unsound data. Retired in S02 by verified smoke test with ≥1 accepted trade.
- **Per-provider JSON parse reliability under realistic game state** — Gemini with complex multi-line prompts may produce fences or partial JSON; DeepSeek R1 reflections embed `<think>` blocks. Tolerant parser must handle all variants before S04's 80-call format ablation. Retired in S03 by exercising all failure modes in pytest.
- **DeepSeek R1 reflection cost** — R1 output is ~5.8× more expensive than V3.2 ($2.19 vs $0.38/1M). 30 Phase 0 games × 5 reflections = up to 150 R1 calls; worst-case cost exceeds D024's $0.45 estimate. The $1.50 Phase 0 budget covers it only if reflection chains stay short. Retired in S04 T01 by monitoring per-game cost and reverting to V3.2 if cost exceeds $0.05/DeepSeek-game.
- **Gemini 429 bursts during format ablation** — 80 calls in quick succession on paid tier. LiteLLM retry handles transient bursts; sustained bursts could exhaust retries. Mitigated in S04 by 0.5s inter-call gap (same pattern as `test_connectivity.py`).

---

## Proof Strategy

- Game mechanics correctness → retire in S02 by running a single all-Mistral 25-round game; manually verify JSONL shows ≥1 accepted+validated trade, ≥1 build, no double-spend in round_end inventory
- JSON parse reliability → retire in S03 by running `pytest tests/test_prompts.py` with synthetic malformed responses covering all 4 failure modes (valid, fenced, mixed-text, truncated)
- R1 cost overrun → retire in S04 by inspecting per-game cost at T01 gate; revert to V3.2 if ≥1 DeepSeek-game exceeds $0.05 total

---

## Verification Classes

- Contract verification: `pytest tests/test_smoke.py` (3-round mock game with stubbed LLM), `pytest tests/test_prompts.py` (parser edge cases)
- Integration verification: single real 25-round Mistral-only game end-to-end; 4-model pairwise game with JSONL model-field spot check
- Operational verification: crash-resume test (kill after round 10, resume, verify round 11 starts clean and no duplicate events)
- UAT / human verification: Phase 0 report Go/No-Go decision requires human review of calibration game behavior before Phase 1 gates open

---

## Milestone Definition of Done

This milestone is complete only when all are true:

- S01 through S05 all have `[x]` in their checklist
- `python scripts/run_game.py --config mistral-mono --games 1` passes acceptance criteria (25 rounds, valid JSONL, ≤$0.02)
- `python scripts/run_game.py --config phase0 --games 30` completes, total cost ≤$1.50
- All 4 providers route correctly in a single pairwise game (verified via JSONL `model` field)
- Crash-resume produces no duplicate JSONL events
- `data/phase0/PHASE0_REPORT.md` written with Go/No-Go recommendation
- OSF formal registration submitted; URL in `data/metadata/osf_registration.json`
- `requirements-lock.txt` committed

---

## Requirement Coverage

- **Covers:** R002 (Trade Island engine — S02), R011 (JSONL logging + schema — S02), R003 (cache-optimized prompts — S03), R004 (Phase 0 calibration — S04), R010 (OSF pre-registration — S05)
- **Partially covers:** R009 (analysis stubs committed in S01; pipeline implementation deferred to M004)
- **Leaves for later:** R005 (Phase 1 — M002), R006 (Phase 2 pairwise — M003), R007 (Phase 2B persona — M003), R008 (Phase 2C full-mix — M003), R012 (paper + open-source — M004)
- **Already complete:** R001 (LiteLLM routing — S01 ✅)
- **Orphan risks:** none — all 12 active requirements have a mapped path

---

## Slices

- [x] **S01: LiteLLM + Environment Setup** `risk:high` `depends:[]`
  > After this: All 4 providers (Groq, OpenRouter/DeepSeek, Google, Mistral) return valid completions; per-provider call signatures and workarounds confirmed and documented in DECISIONS.md D018–D022. ✅ COMPLETE

- [x] **S02: Trade Island Engine** `risk:high` `depends:[S01]`
  > After this: `python scripts/run_game.py --config mistral-mono --games 1` runs a complete 25-round game, writes valid JSONL to `data/raw/{game_id}/game.jsonl`, saves per-round checkpoints, and costs ≤$0.02 — verified by inspecting the log file directly. ✅ COMPLETE

- [ ] **S03: Prompt Templates + Tolerant Parser** `risk:medium` `depends:[S02]`
  > After this: all 6 prompt functions (agent_action, trade_response, gm_resolution, building_decision, reflection, json_utils) are implemented; `pytest tests/test_prompts.py` passes all edge-case parse tests; token counts are within 20% of blueprint targets; the game engine uses these templates for all subsequent runs.

- [ ] **S04: Phase 0 Calibration (30 games)** `risk:medium` `depends:[S02,S03]`
  > After this: 30 calibration games are complete with valid JSONL logs; format decision (compact vs verbose) is locked per model in DECISIONS.md; GM confound is quantified; `data/phase0/PHASE0_REPORT.md` contains a Go/No-Go recommendation for Phase 1; total cost ≤$1.50.

- [ ] **S05: OSF Pre-Registration** `risk:low` `depends:[S02]`
  > After this: OSF formal registration is submitted (timestamp-locked), registration URL is recorded in `data/metadata/osf_registration.json`, GitHub repo is public and linked from OSF, and Phase 1 (M002) is unblocked on the scientific integrity constraint.

---

## Boundary Map

### S01 → S02

Produces:
- Verified `litellm.completion()` call signatures for all 4 providers (exact kwarg sets in `scripts/test_connectivity.py`)
- `litellm.drop_params = True` pattern confirmed working
- `_hidden_params["response_cost"]` cost tracking pattern confirmed
- `strip_md()` JSON fence stripper utility
- `.env` with all 4 API keys; `config/litellm_config.yaml` authoritative per-provider config
- `src/simulation/__init__.py` (empty, ready for module exports)

Consumes:
- nothing (S01 is the base)

### S02 → S03

Produces:
- `src/simulation/` — 6 modules: `config.py`, `llm_router.py`, `agent.py`, `gm.py`, `game.py`, `logger.py`
- `scripts/run_game.py` — CLI entry point with `--config` and `--games` args
- `data/raw/{game_id}/game.jsonl` schema — finalized and documented; columns match analysis stubs (`game_id`, `model_family`, `round`, `agent_id`, `vp`, `inventory_value`)
- `tests/test_smoke.py` — 3-round mock game with stubbed LLM responses; passes with `pytest`
- `GameConfig` named configs: `mistral-mono`, `phase0`, `pairwise-{A}-{B}`
- `data/raw/{game_id}/checkpoint_r{N:02d}.json` — checkpoint schema (full game state)

Consumes:
- `litellm.completion()` call signatures from S01
- `.env` API keys from S01

### S03 → S04

Produces:
- `src/prompts/` — 6 prompt modules: `agent_action.py`, `trade_response.py`, `gm_resolution.py`, `building_decision.py`, `reflection.py`, `json_utils.py`
- `parse_agent_response(raw, schema)` — tolerant parser handling: valid JSON, fenced JSON, JSON with surrounding text, truncated JSON (returns None on failure)
- `get_completion_kwargs(model_family)` — returns correct per-provider litellm kwargs (Gemini gets `thinking`, not `response_format`)
- `tests/test_prompts.py` — all edge cases passing
- Stable static prompt prefixes — byte-for-byte identical across same call type for cache hits

Consumes:
- JSONL event schema from S02 (prompt variable names must match schema fields)
- `GameConfig` from S02 (template rendering uses game config constants)

### S02 → S05

Produces:
- JSONL schema (analysis stubs in `src/analysis/` already reference `[game_id, model_family, round, agent_id, vp, inventory_value]` — S02 must emit exactly these field names)

Consumes:
- Analysis stubs already committed from S01 (commit `c4a9a1d`) — S05 links these to OSF without modifying them

### S04 → S05

Produces:
- Phase 0 game data (JSONL) confirming simulation mechanics are sane before OSF registration finalizes
- `data/phase0/PHASE0_REPORT.md` with Go/No-Go for Phase 1

Consumes:
- OSF registration may proceed before S04 completes (no hard dependency); S05 `depends:[S02]` only for JSONL schema lock
- Note: S05 must be submitted before M002 Phase 1 games begin — the constraint is on M002 start, not on S04 completion

---

## Planning Notes

**Why S02 before S03:** The game engine (S02) finalizes the JSONL schema and the variable set that prompt templates must reference. Designing prompts before the schema is stable risks mismatched field names. S03 depends on S02 schema output as a stable surface.

**Why S03 before S04:** The format ablation in S04 T01 exercises exactly the S03 templates with realistic game state. Running format ablation before the parser is hardened would mix two failure modes (bad template vs bad parser), making diagnosis impossible.

**Why D023 is already settled:** The existing S02 sketch still mentions a "Concordia marketplace evaluation decision gate." This is closed — D023 is recorded in DECISIONS.md. S02 goes directly to building the custom loop with no re-evaluation. The sketch's T02 task (marketplace evaluation) is eliminated.

**S05 parallelism note:** OSF registration can technically start once the JSONL schema is locked (S02). In practice, creating the OSF account and writing `docs/osf_preregistration.md` can happen during S03/S04. The hard constraint is that the formal OSF registration must be **submitted** before any Phase 1 game data exists — i.e., before M002 starts. S05 is last in sequence to match execution order but does not require S04 to complete.

**DeepSeek R1 cost revisit:** D024 estimated ~$0.45 extra for Phase 0. The research note in M001-RESEARCH.md flags this could approach $8 if most Phase 0 games are DeepSeek-mono. Phase 0 has only 5 DeepSeek calibration games + format ablation calls (no reflections). Actual R1 risk in Phase 0 is low (~$0.075 worst case). Phase 1 (M002) is the real R1 cost exposure.
