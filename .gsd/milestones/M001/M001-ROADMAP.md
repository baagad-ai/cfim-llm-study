# M001: Infrastructure + Phase 0

**Vision:** Complete simulation stack validated with 30 calibration games, OSF pre-registered, ready to begin Phase 1 production runs.

---

## Success Criteria

- `python scripts/run_game.py --config mistral-mono --games 1` completes 25 rounds, writes valid JSONL, costs ≤$0.02
- Simulation produces VP in 3–9 range (not −17 to −20) with trade acceptance >15% — verified with v2 engine mechanics
- `python scripts/run_game.py --config phase0 --games 30` completes all 30 calibration games, total cost $0.00–$1.50
- All 4 model families (Llama, DeepSeek, Gemini, Mistral) participate in a single pairwise game; per-agent LLM routing verified by inspecting JSONL `model` fields
- Crash-resume tested: kill mid-game, resume from checkpoint, correct round continuation with no duplicate JSONL events
- GM confound quantified with ≥10 Llama-GM sensitivity games (upgraded from 5 per audit recommendation)
- OSF pre-registration confirmation URL recorded in `data/metadata/osf_registration.json`
- `requirements-lock.txt` committed with all exact pinned versions

---

## Key Risks / Unknowns

- **Game mechanics correctness** — Trade Island has a double-spending race condition across simultaneous proposals. GM resolution must validate trades sequentially against post-prior-trade inventory, not start-of-round snapshot. If this is wrong, experiments produce unsound data. Partially retired in S02: double-spend guard verified by inline test and test_smoke.py mock; live trade acceptance path unverified (D037 — all 115 Mistral proposals declined). Full retirement requires ≥1 accepted trade in S04 calibration with S03-improved prompts.
- **Per-provider JSON parse reliability under realistic game state** — Gemini with complex multi-line prompts may produce fences or partial JSON; DeepSeek R1 reflections embed `<think>` blocks. Tolerant parser must handle all variants before S04's 80-call format ablation. Retired in S03 by exercising all failure modes in pytest.
- **DeepSeek R1 reflection cost** — R1 output is ~5.8× more expensive than V3.2 ($2.19 vs $0.38/1M). 30 Phase 0 games × 5 reflections = up to 150 R1 calls; worst-case cost exceeds D024's $0.45 estimate. The $1.50 Phase 0 budget covers it only if reflection chains stay short. Retired in S04 T01 by monitoring per-game cost and reverting to V3.2 if cost exceeds $0.05/DeepSeek-game.
- **Gemini 429 bursts during format ablation** — 80 calls in quick succession on paid tier. LiteLLM retry handles transient bursts; sustained bursts could exhaust retries. Mitigated in S04 by 0.5s inter-call gap (same pattern as `test_connectivity.py`).

---

## Proof Strategy

- Game mechanics correctness → partially retired in S02 (double-spend guard + 25-round completion verified); full retirement requires ≥1 live accepted trade in S04 Phase 0 calibration games after S03 prompt improvements (D037)
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

- S01 through S07 all have `[x]` in their checklist
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
  > ✅ COMPLETE. All 4 providers verified, API keys configured, cost tracking confirmed.

- [x] **S02: Trade Island Engine** `risk:high` `depends:[S01]`
  > ✅ COMPLETE. 25-round custom game loop, JSONL logging, checkpoints, double-spend guard verified.

- [x] **S03: Prompt Templates + Tolerant Parser** `risk:medium` `depends:[S02]`
  > ✅ COMPLETE. All 6 prompt modules, tolerant parser, 23/23 tests pass, phase0 config updated.

- [~] **S04: Phase 0 Calibration (partial)** `risk:high` `depends:[S02,S03]`
  > ✅ T01 (cost tracking, crash-resume), ✅ T02 (format ablation, D041–D046 locked).
  > T03-FIX SUPERSEDED by S05 full rebuild. Format decisions (D041–D046) and crash-resume infrastructure preserved.
  > T05 (30-game run) and T06 (report) blocked until S05 validation complete.

- [ ] **S05: Simulation Engine v2 — Full Rebuild** `risk:high` `depends:[S02,S03,S04/T01,S04/T02]`
  > Rebuild from first principles: broadcast+match agent-initiated trade, resource degradation (spoilage + destitution), RULES_BLOCK shared prompt rules, structured memory + reflection, RoundMetrics observability.
  > After this: VP in 3–9 range, trade acceptance >15%, broadcast/spoilage/round_metrics events in JSONL, `pytest` 0 failures. Gates 30-game Phase 0 run and OSF registration.

- [ ] **S06: 30-Game Phase 0 Run + Report** `risk:medium` `depends:[S05]`
  > Run 30 phase0 calibration games. Verify >10% trade acceptance, 4-provider routing, ≥10 Llama-GM sensitivity games. Write PHASE0_REPORT.md with Go/No-Go decision for Phase 1.
  > Previously T05+T06 in S04. Renumbered after S05 was inserted.

- [ ] **S07: OSF Pre-Registration** `risk:low` `depends:[S02]`
  > Submit formal OSF pre-registration before any Phase 1 games begin. Lock analysis stubs, record registration URL. Previously S05.
  > Note: Can run in parallel with S06 — hard constraint is submission before M002 starts.

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
- `tests/test_smoke.py` — 5 mock-mode tests covering schema, cost, checkpoint, double-spend; passes with `pytest`
- `GameConfig` named configs: `mistral-mono`, `phase0` (placeholder — see note), `pairwise-{A}-{B}`
- `data/raw/{game_id}/checkpoint_r{N:02d}.json` — checkpoint schema (full game state)

**Note — phase0 config is a placeholder:** `GameConfig.from_name('phase0')` currently returns a mistral-mono config. S03 must update this to the real 4-family mix before S04 calibration games can run. Failing to do so means all 30 calibration games run as mistral-mono, which does not satisfy the 4-model pairwise success criterion.

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

**S07 parallelism note:** OSF registration (S07) can technically start once the JSONL schema is locked (S02). In practice, creating the OSF account and writing `docs/osf_preregistration.md` can happen during S05/S06. The hard constraint is that the formal OSF registration must be **submitted** before any Phase 1 game data exists — i.e., before M002 starts. S07 is last in sequence to match execution order but does not require S06 to complete. S06 (30-game run) and S07 (OSF registration) can run in parallel.

**DeepSeek R1 cost revisit:** D024 estimated ~$0.45 extra for Phase 0. The research note in M001-RESEARCH.md flags this could approach $8 if most Phase 0 games are DeepSeek-mono. Phase 0 has only 5 DeepSeek calibration games + format ablation calls (no reflections). Actual R1 risk in Phase 0 is low (~$0.075 worst case). Phase 1 (M002) is the real R1 cost exposure.
