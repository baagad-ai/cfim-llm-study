# M001: RNE Engine + Phase 0 Calibration

**Vision:** Complete RNE simulation stack validated with 240 Phase 0 sessions. OSF pre-registered. Study 2 (Harbour) engine built. Ready to begin Study 1 full CFIM data collection (M002).

**Design authority:** `.gsd/SIMULATION_DESIGN.md` — all implementation follows this document.

---

## Success Criteria

- [x] `pytest tests/test_rne.py tests/test_rne_prompts.py` — 165+ tests pass
- [x] `python scripts/run_rne.py --family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1` — completes 35 rounds, ≥1 accepted trade, cost ≤$0.05
- [x] Phase 0: 244 sessions complete; ≥90% JSON parse rate per family; calibration report written; Go decision
- [x] OSF registration submitted; URL `https://osf.io/9354h`; GitHub `https://github.com/baagad-ai/cfim-llm-study`
- [ ] Study 2 engine: `python scripts/run_game.py --config phase0 --games 5` → VP in 3–9 range, trade acceptance >15%

---

## Key Risks

- **Zero trade acceptance** — RETIRED ✅ Smoke run (session 3230fd13): mistral×llama Condition A, 1 accepted trade, cost $0.007
- **Gemini parse instability** — RETIRED ✅ Phase 0: Gemini 100% parse rate across 61 sessions
- **Disclosure effect too small to detect** — Phase 0 gives early signal; formal test is M002. Acceptable if null.
- **Study 2 engine acceptance rate** — S05 target: >15% trade acceptance in Harbour game

---

## Proof Strategy

- Trade acceptance → DONE: session 3230fd13, ≥1 `trade_executed` event confirmed
- Prompt format reliability → DONE: Phase 0 parse rates 99.95–100% across all 4 families
- Disclosure effect → qualitative signal in Phase 0 report; formal test is M002
- Study 2 validity → S05/T06: 5-game validation, VP 3–9, acceptance >15%

---

## Slices

- [x] **S01: RNE Engine + LLM Router** `risk:high` `depends:[]`
  > COMPLETE. `run_rne.py` CLI works. Real smoke run: mistral×llama, 35 rounds, 1 accepted trade, cost $0.007. 165 tests pass.

- [x] **S02: RNE Prompt Architecture** `risk:medium` `depends:[S01]`
  > COMPLETE. `build_system_prompt` (9 variants), `build_round_messages` with disclosure injection, `parse_rne_response` (4-strategy tolerant parser). 165 tests pass.

- [x] **S03: Phase 0 Calibration** `risk:medium` `depends:[S01,S02]`
  > COMPLETE. 244 sessions (4 families × 10 reps × 3 conditions × 2 disclosure). Parse rate 99.95–100% per family. Go/No-Go: GO. Report: `data/phase0/calibration_report.md`.

- [x] **S04: OSF Pre-Registration** `risk:low` `depends:[S01]`
  > COMPLETE. Registration live: https://osf.io/9354h. GitHub: https://github.com/baagad-ai/cfim-llm-study. Commit: ca3b54426f70fd7554ae11d7f51927d85b61c95c. H1–H5 stubs committed pre-data.

- [ ] **S05: Study 2 Engine (Harbour v2)** `risk:medium` `depends:[S01]`
  > Build Trade Island simulation from first principles: broadcast+match market, spoilage/destitution degradation, structured memory, full observability. Design doc: `docs/plans/2026-03-15-simulation-engine-v2-design.md`.
  > After this: `pytest tests/` passes; 5-game validation shows VP 3–9, acceptance >15%.

---

## S01 — RNE Engine + LLM Router

**Status:** COMPLETE

### Tasks

- [x] **T01: Config, Logger, and LLM Router** `est:1h`
  > `RNEConfig` (7-family validated), `GameLogger`, `call_llm` + 7-family `PROVIDER_KWARGS`. Tests pass.

- [x] **T02: RNE Engine** `est:2h`
  > `src/simulation/rne_game.py` — `RNERunner.run_session()`: 35-round loop, simultaneous proposals, compatibility check, respond call, trade settlement, 10% decay, perturbation at round 20. Tests pass.

- [x] **T03: Metrics (M1–M4)** `est:1h`
  > `_compute_metrics()` in `rne_game.py`. M1=cooperation_rate, M2=exploitation_delta, M3=adaptation_lag, M4=betrayal_recovery. Covered by engine integration tests.

- [x] **T04: run_rne.py CLI + smoke run** `est:1h`
  > `scripts/run_rne.py` CLI complete. Real smoke run: mistral×llama, condition A, blind, neutral. Session 3230fd13: 35 rounds, M1=0.0286 (1 accepted trade), cost=$0.007. Verified.

---

## S02 — RNE Prompt Architecture

**Status:** COMPLETE

### Tasks

- [x] **T01: System prompt variants — 3 conditions × 3 framings** `est:1h`
  > `build_system_prompt(condition, framing)` — 9 LRU-cached variants, all ≤300 tok, ValueError on unknown inputs.

- [x] **T02: Round messages + disclosure injection** `est:1h`
  > `build_round_messages(...)` — system+user message pair per round; disclosed condition injects opponent family name into user message only.

- [x] **T03: Tolerant parser + full test suite + smoke run** `est:45m`
  > `parse_rne_response(raw)` — 4-strategy fallback: direct parse → fence strip → bracket-counter → None. 165 tests pass. Smoke run verified.

---

## S03 — Phase 0 Calibration

**Status:** COMPLETE

### Tasks

- [x] **T01: run_phase0.py + 4-family test run** `est:1h`
  > `scripts/run_phase0.py` built and tested. 4-family routing verified.

- [x] **T02: Full 240-session run** `est:30m (wall time)`
  > 244 sessions completed (4 extra due to retries). All families routed correctly.

- [x] **T03: Calibration report** `est:45m`
  > `data/phase0/calibration_report.md` written. Parse rates: deepseek 99.95%, gemini/llama/mistral 100%. Go/No-Go: **GO**.

---

## S04 — OSF Pre-Registration

**Status:** COMPLETE

### Tasks

- [x] **T01: Write pre-registration document and analysis stubs** `est:2h`
  > `docs/osf_preregistration.md` (2934 words). Analysis stubs H1–H5 in `src/analysis/`. `data/metadata/osf_registration.json` placeholder.

- [x] **T02: Create OSF project and submit formal registration** `est:1h`
  > Registration submitted at https://osf.io/9354h. Public, immediate, MIT license.

- [x] **T03: Record URL + commit** `est:10m`
  > `data/metadata/osf_registration.json` updated. README and preregistration doc updated. Committed at 0a4e063.

---

## S05 — Study 2 Engine (Harbour v2)

**Status:** NOT STARTED. Next active slice.

**Design doc:** `docs/plans/2026-03-15-simulation-engine-v2-design.md`
**Key decisions:** D048–D055 in `.gsd/DECISIONS.md`

### Must-Haves

- `GameConfig` v2 with: `base_production`, `hoard_bonus`, `win_vp=10`, `perishable_resources`, `perishable_threshold`, `destitution_penalty_vp`, `broadcast_phase`, `stream_events`
- `GameState` dataclass — immutable per-round snapshot used by all agents
- Broadcast phase before act phase each round (D052)
- Agent-initiated trade: act() prompt shows market board; proposals targeted on declared need
- Spoilage: grain/fiber > threshold → decay by 1 per round (logged as spoilage events)
- Destitution: all-zero non-grain inventory → −1VP penalty per round
- `RULES_BLOCK` shared constant (D051) imported by all prompt modules
- Structured JSON reflection output (D053): `{survival_plan, next_building, best_trade_target, trade_strategy, relationships}`
- `RoundMetrics` per round (D054): `{gini, trade_acceptance_rate, avg_vp, vp_std, starvation_count, spoilage_count}`
- `pytest tests/` passes (0 failures); 5-game validation VP 3–9, acceptance >15%

### Tasks

- [ ] **T01: GameConfig v2 + GameState dataclass** `est:1h`
- [ ] **T02: Economy mechanics — production, spoilage, destitution** `est:1.5h`
- [ ] **T03: Broadcast phase + agent-initiated trade** `est:1.5h`
- [ ] **T04: Prompt rebuild — RULES_BLOCK + all prompt modules** `est:2h`
- [ ] **T05: Memory system + observability (RoundMetrics, dashboard)** `est:1.5h`
- [ ] **T06: Integration tests + 5-game validation** `est:1h + 30m wall`

### S05 Verification

```bash
pytest tests/ -v
# → 0 failures

python scripts/run_game.py --config phase0 --games 5
# → VP range 3–9 at round 25; trade acceptance >15%; round_metrics events in JSONL

python3 -c "
import json, pathlib, statistics
summaries = list(pathlib.Path('data/raw').glob('*/game.jsonl'))
print(f'{len(summaries)} games found')
"
```

---

## Planning Notes

**S05 is the only remaining slice in M001.** S01–S04 are complete.

**S05 scope:** Study 2 (Harbour) engine only. The RNE engine (Study 1) is complete and validated. S05 builds the 6-agent multi-agent game used for H5 (ecological validity). Do not modify `src/simulation/rne_game.py` or Study 1 infrastructure in S05.

**S07 in slice directory:** S07 is a stale duplicate of the OSF pre-registration work (now complete as S04). It should not be executed. The canonical completed slice is S04.

**M002 starts after S05 completes.** M002 = Study 1 full CFIM run (3,360 sessions across 28 pairings × 3 conditions × 2 disclosure × 20 runs).
