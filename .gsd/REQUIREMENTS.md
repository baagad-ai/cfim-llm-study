# Requirements

Capability and coverage contract for the CFIM study.
Active = must complete. Deferred = post-paper. Out of scope = never.
Design authority: `.gsd/SIMULATION_DESIGN.md`.

---

## Active

### R001 — LiteLLM Multi-Provider Routing (7 families)
- Class: core-infrastructure
- Status: active
- Description: Single `call_llm(family, messages)` entry point routes to all 7 CFIM families via LiteLLM. Per-provider kwargs enforced (thinking=disabled for Gemini, json_object for all, max_tokens). float cost guard. `litellm.drop_params=True`. $80 hard cap.
- Why it matters: Without reliable routing, every provider failure breaks sessions. The 7-family surface is the foundation every experiment depends on.
- Source: SIMULATION_DESIGN.md §3.5
- Primary owning slice: M001/S01
- Supporting slices: none
- Validation: validated
- Notes: `call_llm`, `PROVIDER_KWARGS` (7 families), `_FAMILY_MODEL` implemented and tested. `test_model_registry_matches_router` asserts sync contract. D047 re-enabled Gemini json_object.

### R002 — RNE Game Engine (Study 1 primary)
- Class: core-infrastructure
- Status: active
- Description: `RNERunner.run_session(config)` runs a 35-round bilateral trading game: simultaneous proposals → compatibility check → respond call → trade settlement → 10% resource decay → round_end logged. Perturbation fires once at round 20. `summary.json` with M1–M4. `metadata.json` with full config. Crash-safe via line-buffered JSONL.
- Why it matters: This is the data-collection engine for all 3,360 Study 1 sessions. Every hypothesis depends on it.
- Source: SIMULATION_DESIGN.md §3.2–§3.4
- Primary owning slice: M001/S01 (T02)
- Supporting slices: M001/S02 (prompts)
- Validation: unmapped
- Notes: T02 is next. T01 (config/logger/router) complete. `src/simulation/rne_game.py` does not yet exist.

### R003 — RNE Prompt Architecture
- Class: core-infrastructure
- Status: active
- Description: `src/prompts/rne_prompts.py` implements: system prompt (static, cache-friendly), neutral/social/strategic framing variants, identity disclosure injection (blind vs disclosed), condition-specific round instructions (A/B/C). Tolerant JSON parser handles fenced/partial responses.
- Why it matters: Prompt quality determines behavioral measurement quality. Cache-friendliness controls cost at 3,360-session scale.
- Source: SIMULATION_DESIGN.md §6
- Primary owning slice: M001/S02
- Supporting slices: none
- Validation: validated
- Notes: `build_system_prompt` (9 LRU-cached variants, all ≤300 tok), `build_round_messages` (disclosure injection in user message only, history truncation), `parse_rne_response` (4-strategy tolerant parser) — all implemented and tested. 118 tests pass. Real smoke run confirms prompt generates valid LLM exchanges at $0.0072/session.

### R004 — CFIM Session Configuration (RNEConfig)
- Class: core-infrastructure
- Status: active
- Description: `RNEConfig` Pydantic model with all Study 1 variables: `family_a`, `family_b`, `condition` (A/B/C), `disclosure` (blind/disclosed), `prompt_framing` (neutral/social/strategic), `rounds=35`, `decay_rate=0.10`, `perturbation_round=20`, `session_id`. Family fields validated against `RNE_FAMILIES` (7 families). `GameConfig.from_rne()` factory.
- Why it matters: The config is the factorial design in code. Wrong fields = wrong experiments.
- Source: SIMULATION_DESIGN.md §3.2
- Primary owning slice: M001/S01 (T01)
- Supporting slices: none
- Validation: validated
- Notes: `RNEConfig` fully implemented with `@field_validator` on family fields. `RNE_FAMILIES` frozenset exported. All 7 families validated in `test_rne.py`.

### R005 — M1–M6 Metrics Computation
- Class: research-phase
- Status: active
- Description: Per-session computation of: M1 cooperation rate, M2 exploitation delta, M3 adaptation lag, M4 betrayal recovery, M5 minimum acceptable offer (Condition C), M6 identity sensitivity (|M1_disclosed − M1_blind|). Written to `summary.json`.
- Why it matters: These are the pre-registered dependent variables. H1–H5 all operate on M1–M6.
- Source: SIMULATION_DESIGN.md §4
- Primary owning slice: M001/S01 (T02)
- Supporting slices: none
- Validation: unmapped
- Notes: M1–M4 computed inside `RNERunner`. M5 requires Condition C sweep. M6 is cross-session (computed at analysis stage, not per-session).

### R006 — Phase 0 Calibration (240 sessions)
- Class: research-phase
- Status: active
- Description: 4 core families (llama, deepseek, gemini, mistral) × 10 sessions × 3 conditions × 2 disclosure = 240 sessions. Verifies: behavioral signal exists, parse rates >90%, cost within budget, perturbation response detectable. Produces `data/phase0/calibration_report.md` with go/no-go for Study 1.
- Why it matters: Catches design defects before committing to 3,360 sessions. If trade rates are 0% or parse fails >10%, the study design needs adjustment.
- Source: SIMULATION_DESIGN.md §3 (Phase 0 note), §8 Q3
- Primary owning slice: M001/S03
- Supporting slices: none
- Validation: unmapped
- Notes: Depends on R002 (engine) and R003 (prompts) complete.

### R007 — JSONL Schema + Data Directory (Study 1)
- Class: data-management
- Status: active
- Description: Each session writes to `data/study1/{session_id}/game.jsonl` (one event per line) + `summary.json` (M1–M4 + config fields) + `metadata.json` (full RNEConfig + wall_clock_seconds). JSONL events: `game_start`, `round_start`, `proposal`, `trade_result`, `decay`, `perturbation`, `round_end` (per agent), `parse_failure`, `game_end`. `game_end` always written via try/finally.
- Why it matters: The JSONL is the audit trail and the analysis input. Schema must be locked before Phase 0 runs — analysis stubs are pre-registered against it.
- Source: SIMULATION_DESIGN.md §9
- Primary owning slice: M001/S01 (T02)
- Supporting slices: M001/S02
- Validation: unmapped
- Notes: Directory structure defined. Events not yet emitted (T02 scope).

### R008 — run_rne.py CLI
- Class: operability
- Status: active
- Description: `scripts/run_rne.py --family-a FAMILY --family-b FAMILY --condition A|B|C --disclosure blind|disclosed --framing neutral|social|strategic --games N [--mock]` runs N sessions and writes all outputs. `--mock` flag enables no-API testing.
- Why it matters: The CLI is the interface to the engine for all 3,360 sessions. Manual invocation and batch scripts both use it.
- Source: SIMULATION_DESIGN.md §9 (scripts/)
- Primary owning slice: M001/S02 (T03)
- Supporting slices: none
- Validation: validated
- Notes: Implemented in M001/S02/T03. Smoke-verified: real Mistral×Llama 35-round session completes, writes game.jsonl + summary.json + metadata.json, cost $0.0072 ≤ $0.05. `--mock` mode runs zero-cost sessions.

### R009 — OSF Pre-Registration
- Class: research-integrity
- Status: active
- Description: Formal OSF registration of H1–H5 submitted with analysis stubs committed before any Study 1 data collected. Registration URL in `data/metadata/osf_registration.json`.
- Why it matters: Pre-registration is the credibility foundation — prevents HARKing accusations. Hard constraint: must complete before M002 starts.
- Source: SIMULATION_DESIGN.md §5
- Primary owning slice: M001/S04
- Supporting slices: none
- Validation: partial
- Notes: `docs/osf_preregistration.md` and analysis stubs committed (D056). OSF formal submission (human action) still pending.

### R010 — Study 1 Full CFIM Data Collection (3,360 sessions)
- Class: research-phase
- Status: active
- Description: 28 unique pairs × 3 conditions × 2 disclosure × 3 framings × 20 sessions = 3,360 sessions. All written to `data/study1/`. Total cost ≤$47. Per-cell: 20 sessions minimum for valid statistics (detects Δ>8.1% cooperation rate at 80% power).
- Why it matters: This is the primary dataset. The CFIM matrix is built from it.
- Source: SIMULATION_DESIGN.md §3.5
- Primary owning slice: M002
- Supporting slices: none
- Validation: unmapped

### R011 — Study 2 Harbour Engine (Ecological Validity)
- Class: research-phase
- Status: active
- Description: 6-agent Harbour game engine. Mono (4 families × 20 games) + mixed compositions designed from Study 1 findings. Tests whether bilateral CFIM patterns predict multi-agent VP variance.
- Why it matters: H5 tests ecological validity. Without Study 2, the paper only has bilateral evidence.
- Source: SIMULATION_DESIGN.md §3.6
- Primary owning slice: M003/S01
- Supporting slices: none
- Validation: unmapped

### R012 — CFIM Analysis Pipeline (H1–H5)
- Class: analysis
- Status: active
- Description: Pre-registered implementations of H1 (Wilcoxon diagonal vs off-diagonal), H2 (LRT mixed-effects logistic), H3 (one-sample t + paired Wilcoxon on |M6|), H4 (Kruskal-Wallis M3 across pairs), H5 (OLS bilateral M1 → Study 2 VP variance). CFIM matrix construction and heatmap generation.
- Why it matters: The analysis is the paper. Without valid stats, there is no contribution.
- Source: SIMULATION_DESIGN.md §4–§5
- Primary owning slice: M004/S01
- Supporting slices: none
- Validation: partial
- Notes: Analysis stubs `h1_self_play_premium.py` through `h5_cfim_to_multiagent.py` committed (pre-registered). Full implementation is M004 scope.

### R013 — Paper + Open-Source Deliverables
- Class: output
- Status: active
- Description: AAMAS 2027 full paper + NeurIPS 2026 workshop short paper + arXiv preprint. Open-source: RNE game environment (pip-installable), CFIM dataset on Hugging Face, analysis notebooks.
- Why it matters: Research impact. The RNE environment as a benchmark is the second major contribution after the paper.
- Source: SIMULATION_DESIGN.md §7
- Primary owning slice: M004/S02-S03
- Supporting slices: none
- Validation: unmapped

---

## Deferred

### R020 — Claude Haiku Inclusion
- Class: extensibility
- Status: deferred
- Description: Add Claude 3.5 Haiku as an 8th CFIM family (would make 8×8 = 64 pairs).
- Why it matters: Additional architectural diversity; Anthropic family representation.
- Source: SIMULATION_DESIGN.md §3.5 (excluded with note)
- Primary owning slice: none
- Validation: unmapped
- Notes: Excluded due to budget constraint ($0.031/session vs avg $0.008). Add if budget increases (e.g. conference travel reimbursement). Would require n=12 sessions/cell to stay within $80.

### R021 — GPT-4o Full (Non-Mini)
- Class: extensibility
- Status: deferred
- Description: Replace gpt4o-mini with full GPT-4o in the family pool.
- Why it matters: Higher capability model; would differentiate OpenAI capability tier effects.
- Source: SIMULATION_DESIGN.md §3.5
- Primary owning slice: none
- Validation: unmapped
- Notes: $0.086/session — 17× cost of gpt4o-mini. Infeasible under $80 cap.

### R022 — Real-Time Monitoring Dashboard
- Class: operability
- Status: deferred
- Description: Live dashboard showing session progress, cost burn, per-cell completion counts, parse failure rates.
- Why it matters: Useful for 3,360-session run monitoring.
- Source: SIMULATION_DESIGN.md §D055
- Primary owning slice: none
- Validation: unmapped
- Notes: `rich` library dashboard designed in D055. Deferred until Study 1 batch runs start (M002).

---

## Out of Scope

### R030 — Human-in-the-Loop Agents
- Class: constraint
- Status: out-of-scope
- Description: No human player agents. All agents are LLM-controlled.
- Why it matters: Defines this as a fully-automated LLM behavioral study, not a human-LLM comparison.
- Source: study design
- Primary owning slice: none
- Validation: n/a

### R031 — Non-RNE Primary Game Types
- Class: constraint
- Status: out-of-scope
- Description: Prisoner's dilemma, auctions, and other game types are not the primary experiment. RNE is the only Study 1 game.
- Why it matters: Controlled single-domain comparison. Other games are future work.
- Source: SIMULATION_DESIGN.md §3.1
- Primary owning slice: none
- Validation: n/a
- Notes: Harbour (Study 2) is in-scope as an ecological validity check, not a standalone primary study.

### R032 — Concordia Integration
- Class: constraint
- Status: out-of-scope
- Description: Concordia entity/component system is not used. Custom game loops call litellm.completion() directly.
- Why it matters: Concordia's `sample_text(prompt: str)` interface is incompatible with per-provider chat kwargs (thinking={}, response_format={}). See D023.
- Source: D023
- Primary owning slice: none
- Validation: n/a

---

## Traceability

| ID | Class | Status | Primary Owner | Validation |
|---|---|---|---|---|
| R001 | core-infrastructure | active | M001/S01 | **validated** — 7-family routing tested, registry sync asserted |
| R002 | core-infrastructure | active | M001/S01 (T02) | unmapped — T02 next |
| R003 | core-infrastructure | active | M001/S02 | **validated** — 118 prompt tests pass; 9 variants ≤300 tok; disclosure injection + parser verified; smoke run at $0.0072 |
| R004 | core-infrastructure | active | M001/S01 (T01) | **validated** — RNEConfig + field_validator + 31 tests pass |
| R005 | research-phase | active | M001/S01 (T02) | unmapped |
| R006 | research-phase | active | M001/S03 | unmapped |
| R007 | data-management | active | M001/S01 (T02) | unmapped |
| R008 | operability | active | M001/S02 (T03) | **validated** — CLI smoke-verified; game.jsonl + summary.json + metadata.json written; mock mode works |
| R009 | research-integrity | active | M001/S04 | partial — stubs + doc committed; OSF submission pending |
| R010 | research-phase | active | M002 | unmapped |
| R011 | research-phase | active | M003/S01 | unmapped |
| R012 | analysis | active | M004/S01 | partial — stubs committed; full implementation M004 |
| R013 | output | active | M004/S02-S03 | unmapped |
| R020 | extensibility | deferred | none | unmapped |
| R021 | extensibility | deferred | none | unmapped |
| R022 | operability | deferred | none | unmapped |
| R030 | constraint | out-of-scope | none | n/a |
| R031 | constraint | out-of-scope | none | n/a |
| R032 | constraint | out-of-scope | none | n/a |

## Coverage Summary

- **Active:** 13 requirements
- **Validated:** 4 (R001, R003, R004, R008)
- **Partially validated:** 2 (R009, R012)
- **Unmapped active:** 7 (R002, R005–R007, R010, R011, R013)
- **Deferred:** 3
- **Out of scope:** 3
- **Total:** 19
