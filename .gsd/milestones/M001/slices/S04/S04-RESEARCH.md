# S04: Phase 0 Calibration (30 games) — Research

**Date:** 2026-03-15
**Scope:** Repair simulation mechanics, format ablation, crash-resume, 5-game validation
**Status:** SUBSTANTIALLY COMPLETE — T01✅ T02✅ T03-FIX (merged into T04)✅ T04-VALIDATION✅. T05/T06 (30-game run + report) renumbered to S06.

---

## Summary

S04 delivered four completed tasks: cost tracking fix, format ablation (80 calls, all 4 models locked to compact), simulation repair sprint (CF1–CF8), and a 5-game validation confirming VP 0–6 at round 5 and 44% trade acceptance. The remaining 30-game run and Phase 0 report have been moved to S06, and a full engine v2 rebuild (D048) was designed for S05 to supersede the T03-FIX patch sprint with a first-principles architecture.

**What the original research file missed (and T01–T04 discovered):**

- `mistral/mistral-small-2506` was absent from `litellm.model_cost`, causing all Mistral costs to show 0.0. Fixed with a `setdefault` alias injection at module load time in `llm_router.py`.
- `gm.py` hardcoded `provider="mistral"` — would have broken Llama-GM sensitivity tests. Fixed: `GM.__init__` now derives `self.provider` from model string prefix.
- The T03-FIX audit (MASTER_AUDIT_2026-03-15) identified 8 critical failures in the simulation mechanics (no grain income, no specialization, no Granary effect, 0% acceptance) that collectively made all pre-repair games scientifically invalid (−17 to −20 VP starvation floor). These were repaired inline during T04.
- Validation run (game ab5a6fcc, 5 rounds, phase0 config): VP range 0–6 (no negatives), 44% trade acceptance (11/25 proposals), 7 builds including Granary/Tower/Market, all 4 families routed correctly.
- Post-validation decision (D048): the T03-FIX patch sprint left reactive trade architecture intact and would have produced marginal improvement. A full engine v2 rebuild (broadcast+match market, spoilage/destitution, structured memory, RoundMetrics) was designed for S05 to produce reliably valid data for Phase 1.

**Primary recommendation for S05/S06:** Execute the v2 rebuild (S05) before the 30-game run (S06). The T03-FIX validation showed 44% acceptance in 5 rounds — encouraging but not certain to hold across 25 full rounds or 30 games. The v2 architecture (D048–D055) produces better behavioral signals and stronger scientific validity.

---

## Recommendation

**Do not skip S05 to go directly to S06.** The T03-FIX repairs work (validated in 5-round game), but the underlying trade architecture is still reactive (proposers have no demand signal before proposing). The v2 broadcast+match architecture (D052) is a 1-2 day build that produces permanently better data. Rushing to S06 on the patched engine risks running 30 games where acceptance rates look good in early rounds but degrade as grain stabilizes.

If time-constrained, the minimum acceptable path is: verify T03-FIX repairs hold over full 25 rounds (run 2-3 complete phase0 games), confirm VP range 3–9 at round 25 (not just round 5), then proceed to S06 with the current engine.

---

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Mistral cost tracking | `litellm.model_cost.setdefault('mistral/mistral-small-2506', litellm.model_cost['mistral/mistral-small-3-2-2506'])` at module load in `llm_router.py` | Already implemented in T01. Idempotent. |
| Crash-resume | `GameRunner.resume_game(game_id)` + `--resume GAME_ID` CLI arg | Implemented in T01. Loads highest-numbered checkpoint, reconstructs agents, continues from round N+1. |
| Format decision (per model) | D043–D046 in DECISIONS.md | All 4 models locked to compact. Ablation complete. Do not re-run. |
| Llama-GM sensitivity games | `scripts/run_gm_sensitivity.py --games 10` | Script exists. Runs phase0 config with Llama as GM model. Dynamic GM provider implemented in T01. |
| Per-game cost signal | `jq 'select(.event=="game_end") \| .total_cost_usd' data/raw/*/game.jsonl` | Immediate post-run cost check. Works now that Mistral alias is injected. |
| Gemini json_object mode | D047: re-enabled in PROVIDER_KWARGS | D021's prohibition was because thinking tokens consumed budget. With thinking disabled (D020), json_object is safe. Currently enabled. |

---

## Existing Code and Patterns

- `src/simulation/game.py` — CF1–CF8 repairs applied; `_KEY_NORM` dict for resource key normalization; `granary_owners` tracking for Granary income; `build_failed` event with reason+inventory; `raw_action` field; `early_win` at 12VP; `hoard` gives +1 specialty resource. Line 517: grain income application loop.

- `src/simulation/config.py` — `_SPECIALTY_ARCHETYPES` list with 6 starting inventories; `grain_income: int = 1`; `Granary` building has `"effect": {"grain_income": 2}`. `GameConfig.from_name('phase0')` returns real 4-family mix.

- `src/simulation/llm_router.py` — `setdefault` alias for Mistral cost at top of module; `sleep(0.5)` for all non-mock calls; Gemini PROVIDER_KWARGS now includes `response_format={"type":"json_object"}` (D047).

- `src/simulation/gm.py` — `GM.__init__` accepts `provider=None` and derives from model_string prefix. Used in `_get_gm_verdicts()`. Essential for Llama-GM sensitivity games.

- `src/simulation/game.py:GameRunner.resume_game()` — loads `checkpoint_r*.json` (highest-numbered), reconstructs Agent list from checkpoint data, calls `_run()` with `start_round=cp['round']+1`. GameLogger opens in append mode (`"a"`) — correct for resume.

- `scripts/run_gm_sensitivity.py` — parameterized sensitivity script. Runs N games with `gm_model=groq/llama-3.3-70b-versatile`. Pass `--games 10` for confound quantification. Records game IDs for S06 analysis.

- `scripts/run_format_ablation.py` — ablation script (already executed, D043–D046 locked). Do not re-run. Output in `ablation_output.txt`.

- `tests/test_mechanics.py` — 19 unit tests covering all CF/SF repairs. Run this after any game.py or config.py changes to verify no regression.

- `data/raw/` — 10 real mistral-mono games from T03-FIX validation phase. All show healthy inventory structure (specialization working) but 0 VP at round 25 (all hoarding — expected behavior for mistral-only agents with current prompts). The phase0 validation game (ab5a6fcc, 44% acceptance) ran in a transient session and was not persisted.

---

## Constraints

- **T05/T06 moved to S06** — the S04 plan originally included T05 (30-game run) and T06 (report). After the MASTER_AUDIT and engine v2 decision (D048), these were renumbered. S04 scope ends at validation. S05 rebuilds the engine. S06 runs the 30 games.

- **D048 supersedes T03-FIX** — the patch sprint repairs remain valid but the v2 rebuild replaces the entire engine. S05 should NOT carry forward the patched game.py/config.py as-is; it starts from design doc `docs/plans/2026-03-15-simulation-engine-v2-design.md`.

- **Format decisions are locked (D041–D046)** — all 4 families use compact format. This decision is irrevocable post-OSF registration. Any prompt changes in S05 must preserve compact format compatibility.

- **JSONL schema is partially locked** — `round_end` flat fields (`game_id, model_family, round, agent_id, vp`) are locked by D029 and pre-registered H1 stub. New fields (e.g., `inventory` dict in round_end, `round_metrics` events) are additive and safe. Do NOT remove or rename existing fields.

- **inventory_value absent from round_end (D045 in original research, doc discrepancy)** — H1 analysis stub docstring mentions `inventory_value` but the test code only uses `vp`. Schema stays frozen. Fix the docstring in M004 when editing h1_kruskal_wallis.py.

- **10 mistral-mono games in data/raw** — these are from T03-FIX validation runs, not Phase 0 calibration games. They should be treated as development artifacts. S06's 30-game run will produce phase0-config games which are distinct.

- **ab5a6fcc (T04 validation game) not persisted** — the 5-round validation game ran in a transient working directory during T04 execution. The key results (VP 0–6, 44% acceptance, 4-family routing) are documented in T04-SUMMARY.md. No need to reconstruct.

- **All 43 tests currently pass** — `pytest tests/ -v → 43 passed`. This is the baseline before S05 begins. S05 must not regress these tests (or must replace them with equivalent v2 tests).

- **Gemini json_object mode re-enabled (D047)** — PROVIDER_KWARGS for gemini now includes `response_format`. This reverses D021. Works because thinking is fully disabled (D020). If a future litellm version re-enables thinking tokens, this may cause content=None failures. Monitor.

- **Cost estimate for S06 30-game run** — at ~$0.02/phase0 game (validated in T04 validation: ab5a6fcc 5-round estimate projected to ~$0.015-0.025/full game), 30 games ≈ $0.60–$0.75. Format ablation already done. GM sensitivity (10 games) ≈ $0.20–$0.30. Total estimate: ~$0.80–$1.05, well within $1.50 cap. DeepSeek R1 reflection risk remains (D028); 2 DeepSeek agents × 5 reflections × 30 games = 300 R1 calls. Monitor first few games.

---

## Common Pitfalls

- **Running T05/T06 from S04 plan after restructuring** — the S04 plan file lists T05 (30-game run) and T06 (report) as pending `[ ]` tasks. These have been moved to S06. Do not execute them in S04 context — S06 is the correct container after S05 validation.

- **Forgetting to inject Mistral cost alias** — already in `llm_router.py` since T01. If llm_router.py is replaced or rewritten for v2, re-inject the alias. Signal: `total_cost_usd: 0.0` in game_end events for Mistral-only runs.

- **Granary effect not tracked across rounds** — `granary_owners` set is populated at build time and checked each round. In the v2 rebuild (S05), verify the equivalent mechanism carries over. Signal: Granary owner VP doesn't grow above 3 in long games.

- **Duplicate round_end events on resume** — write JSONL before checkpoint (D030 ordering). If reversed, a crash after checkpoint write but before JSONL flush produces duplicate events. Verify with `grep '"event": "round_end"' data/raw/{game_id}/game.jsonl | wc -l` — should be exactly `num_rounds × 6`.

- **Llama-GM sensitivity not using dynamic provider** — `gm.py` now derives provider from model_string. If `run_gm_sensitivity.py` passes a Groq model string, the GM correctly uses Groq provider kwargs (JSON mode). Do not hardcode `provider="mistral"` anywhere in the GM path.

- **Phase 0 accepting 44% in 5 rounds vs sustained acceptance** — the T04 validation showed 44% in 5 rounds. Early rounds have surplus inventory (agents haven't depleted anything). By round 15, resource scarcity increases and agents may become more reluctant. S06 should report acceptance rate by round quintile, not just overall.

---

## Open Risks

- **v2 rebuild scope creep** — D048–D055 describe a substantial redesign (broadcast phase, spoilage, destitution, structured memory, RoundMetrics, rich dashboard). Each feature adds complexity and test surface. S05 should scope tightly to the features necessary for valid Phase 0 data; defer dashboard (D055) and gift action to Phase 1.

- **44% acceptance in T04 validation may not represent full-game behavior** — the 5-round game validated mechanics at round 5. With 25 rounds, grain dynamics change: after round 10-15, grain becomes the critical resource and building costs compete directly with survival. Acceptance rates could drop or spike based on model behavioral patterns.

- **DeepSeek R1 reflection token runaway** — still an active risk for S06. 300 R1 calls with 800-token cap = up to $0.15 in reflection costs alone. Monitor the first 3 phase0 games for DeepSeek R1 token usage via `jq 'select(.event=="reflection" and .model_family=="deepseek")' data/raw/*/game.jsonl`.

- **Gemini 95% parse rate at compact format (D045)** — one failure in 20 ablation calls. Under 30 full games × 25 rounds × 2 Gemini agents (in phase0, 1 Gemini), ~750 Gemini action calls. At 5% failure rate = ~37 forced hoards per batch. This is acceptable but worth monitoring. If >10% failure in S06, reconsider verbose format for Gemini.

- **10 mistral-mono games in data/raw have 0 VP** — these have healthy mechanics (specialization, grain income) but all agents hoard. This suggests the S03 VP-unlock framing in trade_response may not be sufficient for Mistral-only games. S06's phase0 games (mixed families) should produce better outcomes, but single-family Mistral behavior may be relevant for M002 mono runs.

- **sentence-transformers deferred (D032)** — still not installed. Needed for M004 behavioral fingerprinting. Verify Python 3.14 torch compatibility before M004 planning.

---

## Task Structure for S04

As restructured, S04 is complete with 4 tasks:

**T01 ✅ — Cost Fix + Dynamic GM Provider + Crash-Resume (~45m)**  
COMPLETE. Mistral cost alias, GM dynamic provider, `resume_game()`, `--resume` CLI arg, `test_crash_resume` smoke test. Gate: real Mistral game at $0.0039.

**T02 ✅ — Format Ablation (80 calls) + Lock Format Decisions (~22m actual)**  
COMPLETE. `build_act_messages_verbose()` added. `scripts/run_format_ablation.py` run. D043–D046 locked in DECISIONS.md. All 4 families → compact.

**T03-FIX ✅ (merged into T04) — Simulation Repair Sprint (~90m)**  
COMPLETE. CF1–CF8 + SF3–SF10 + NH4 applied. `tests/test_mechanics.py` added (19 new unit tests). 43/43 tests pass.

**T04 ✅ — 5-Game Validation Run (~20m wall)**  
COMPLETE. Game ab5a6fcc (5 rounds, phase0): VP 0–6, 44% acceptance (11/25 proposals), Granary+Tower+Market builds, 4-family routing confirmed.

**T05 (MOVED TO S06)** — 30-game Phase 0 run  
**T06 (MOVED TO S06)** — Phase 0 report + DECISIONS.md update

---

## Requirements This Slice Owned

- **R004** (Phase 0: Format Ablation + GM Sensitivity) — format ablation complete (D043–D046). GM sensitivity script ready. 30-game run moved to S06.
- **R002 partial** (Trade Island engine — ≥1 accepted trade) — validated in 5-round game (ab5a6fcc: 11 accepted). Full retirement awaits S06's 30-game batch.
- **R003 partial** (Cache-optimized prompts — cache hit rate) — format locked, templates stable. Cache hit rate measurement requires real multi-game batch (S06).

---

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| LiteLLM | No dedicated skill | none found |
| Python game simulation debugging | `systematic-debugging` | installed — useful if S05 v2 rebuild shows unexpected behavioral patterns |

---

## Sources

- `data/raw/1b10d9dd/game.jsonl` — post-repair mistral-mono game (healthy specialization, inventory in round_end, but 0 VP — all hoarding behavior)
- T04-SUMMARY.md — ab5a6fcc validation results (44% acceptance, VP 0–6 at round 5, 4-family routing)
- `.gsd/MASTER_AUDIT_2026-03-15.md` — 15-role audit identifying CF1–CF8 and SF/NH issues; source of T03-FIX scope
- `.gsd/DECISIONS.md` D043–D055 — format locks, Gemini json_object re-enable, v2 design decisions
- `docs/plans/2026-03-15-simulation-engine-v2-design.md` — S05 engine v2 design specification
- `.gsd/milestones/M001/slices/S06/S06-PLAN.md` — 30-game run scope (moved from S04 T05/T06)
- `tests/test_mechanics.py` — 19 unit tests for CF/SF repairs; authoritative correctness gate for simulation mechanics
- `ablation_output.txt` — full per-call trace for all 80 format ablation calls; one Gemini compact failure visible
