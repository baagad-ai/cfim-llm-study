# Requirements

Research capability contract and coverage. Active = must complete. Deferred = post-paper. Out of scope = never.

---

## Active

### R001 — LiteLLM Multi-Provider Routing
- Class: core-infrastructure
- Status: active
- Description: Single LiteLLM router handles all 4 providers (Groq, DeepSeek, Google, Mistral). Automatic retry (3×, 2s backoff), $80 hard budget cap, per-provider JSON mode enforcement, cost logging.
- Why it matters: Without reliable routing, every provider failure cascades into broken games. The budget cap is a safety net for a ₹12,500 total budget.
- Source: blueprint §1, §6
- Primary owner: M001/S01
- Validation: unmapped

### R002 — Trade Island Simulation Engine
- Class: core-infrastructure
- Status: active
- Description: Custom 6-module simulation loop (not Concordia — see D023) running Trade Island. Sequential GM resolution, per-agent LLM routing, per-round checkpoint saves, structured JSONL logging. 25-round game loop validated with real Mistral API calls.
- Why it matters: Custom loop gives full control over per-provider LLM kwargs required by D018–D022. Concordia's text-only interface was incompatible with chat-completion arguments.
- Source: blueprint §3, §6
- Primary owner: M001/S02
- Validation: M001/S02 — `python scripts/run_game.py --config mistral-mono --games 1` completed; 150 round_end lines; 25 checkpoints; total_cost_usd=0.0 (≤$0.02). Double-spend prevention verified by inline test and test_smoke.py. Partially validated — ≥1 accepted trade not yet confirmed in live run (D037; Phase 0 calibration pending).

### R003 — Cache-Optimized Prompt Templates
- Class: performance-optimization
- Status: active
- Description: All prompts use prefix-first structure (static → semi-static → dynamic) to maximize cache hit rates: 60-70% input token savings. Agent (~90 tok), Trade response (~60 tok), GM (~120 tok), Reflection (~150 tok) templates implemented per blueprint §2.
- Why it matters: Cache hits drop total cost from ~$80 to ~$32. Difference between within-budget and over-budget.
- Source: blueprint §2
- Primary owner: M001/S03
- Validation: unmapped

### R004 — Phase 0: Format Ablation + GM Sensitivity
- Class: research-phase
- Status: active
- Description: 80 format-test calls (20/model, verbose vs compact), decision rule at 90% JSON parse threshold, 10 GM-sensitivity games (Mistral GM vs Llama GM), cost ~$0.50. Outputs: confirmed prompt format per model, GM confound quantification.
- Why it matters: If compact prompts fail on any model, must use verbose for that model. If GM confound is large, pairwise results need correction.
- Source: blueprint §4 Phase 0
- Primary owner: M001/S04
- Validation: unmapped

### R005 — Phase 1: 120 Monoculture Games
- Class: research-phase
- Status: active
- Description: 30 games per model family (Llama, DeepSeek, Gemini, Mistral), 6 agents same family per game, 25 rounds each. ~8-10 calendar days at 15/day. Resource specialty assignments randomized and recorded.
- Why it matters: Baseline behavioral signatures. Without monoculture data, pairwise comparisons have no reference point.
- Source: blueprint §4 Phase 1
- Primary owner: M002
- Validation: unmapped

### R006 — Phase 2: 150 Pairwise Games (6 Pairs × 25)
- Class: research-phase
- Status: active
- Description: All 6 cross-family pairings (Llama×DeepSeek, Llama×Gemini, Llama×Mistral, DeepSeek×Gemini, DeepSeek×Mistral, Gemini×Mistral). 3v3 configuration with complementary resource specialties. 25 games per pair.
- Why it matters: The primary research contribution. Pairwise heatmaps are the paper's signature figures.
- Source: blueprint §4 Phase 2
- Primary owner: M003/S01
- Validation: unmapped

### R007 — Phase 2B: Persona-vs-Architecture Experiment (20 games)
- Class: research-phase
- Status: active
- Description: Identical prompts, different models vs identical models, different persona prompts. Permutation-based variance comparison on 5 metrics: VP, trade acceptance, Gini, exploitation index, cooperation tendency.
- Why it matters: Provides causal evidence that architecture (not prompt) drives behavioral signatures. H4 tests this.
- Source: blueprint §4 Phase 2B
- Primary owner: M003/S02
- Validation: unmapped

### R008 — Phase 2C: Full-Mix + Temporal Validation (15 games)
- Class: research-phase
- Status: active
- Description: 15 games with all 4 families mixed (novel condition), temporal validation runs to detect model drift between Phase 1 and Phase 2.
- Why it matters: Temporal validation addresses Limitation #5 (API model instability). All runs timestamped; comparison detects drift.
- Source: blueprint §4 Phase 2C
- Primary owner: M003/S03
- Validation: unmapped

### R009 — Statistical Analysis Pipeline
- Class: analysis
- Status: active
- Description: Pre-registered analysis: Kruskal-Wallis (H1), logistic mixed-effects (H2), one-sample t-test BH-corrected (H3), permutation variance comparison (H4). 4×4 pairwise heatmaps, behavioral drift detection (5-round windows), three-track classifier (behavior/language/meta-behavioral).
- Why it matters: Stats without pre-registration = HARKing risk. Scripts must be committed to OSF before Phase 1.
- Source: blueprint §4 (pre-registration), §5
- Primary owner: M004/S01
- Validation: unmapped

### R010 — OSF Pre-Registration
- Class: research-integrity
- Status: active
- Description: Create OSF account, register hypotheses H1-H4, commit analysis stub scripts before Phase 1 begins. Timestamp-locked.
- Why it matters: Pre-registration is the credibility foundation. Without it, reviewers will suspect post-hoc hypothesis selection.
- Source: blueprint §4 (pre-registration section)
- Primary owner: M001/S05
- Validation: unmapped

### R011 — Structured JSON Logging + Data Pipeline
- Class: data-management
- Status: active
- Description: Every game produces a structured JSONL file: per-round agent decisions, trade proposals/outcomes, VP deltas, inventory states, GM resolutions, reflection summaries. Data pipeline ingests into Polars dataframes for analysis.
- Why it matters: 335 games × 25 rounds × 6 agents = ~50K data points. Manual data cleaning is not feasible.
- Source: blueprint §6 (Concordia v2.0 JSON logging)
- Primary owner: M001/S02 (schema), M002/S01 (validation), M004/S01 (pipeline)
- Validation: M001/S02 — JSONL schema locked. Events: game_start, round_start, agent_action, gm_resolution, build, grain_consumption, reflection, round_end, game_end. round_end flat fields `game_id, model_family, round, agent_id, vp` confirmed by test_smoke.py assertions and live grep. 9 H2 fields confirmed in gm_resolution events. Polars pipeline ingestion not yet validated (M002/S01 scope).

### R012 — Paper + Open-Source Deliverables
- Class: output
- Status: active
- Description: NeurIPS 2026 workshop short paper + AAMAS 2027 full paper + arXiv preprint. Open-source: concordia-pairwise library, model-pairwise-benchmark tool, trade-island-dataset on Hugging Face.
- Why it matters: Research impact. The open-source tools multiply the contribution beyond the paper.
- Source: blueprint §11
- Primary owner: M004/S02, M004/S03
- Validation: unmapped

---

## Deferred

### R020 — GPT-4o / Claude Inclusion
- Class: extensibility
- Status: deferred
- Description: Add closed-source model families to the pairwise matrix.
- Source: blueprint §7 Limitation #8
- Notes: Budget and scope excluded closed-source. Future work.

### R021 — Larger Agent Groups (>6)
- Class: extensibility
- Status: deferred
- Description: Scale to 12 or 24 agents for macro-simulation dynamics.
- Source: blueprint §7 Limitation #2
- Notes: Computational experimental economics scale. Not v1 scope.

### R022 — Real-Time Dashboard
- Class: tooling
- Status: deferred
- Description: Live web dashboard showing game progress, cost burn, per-model stats.
- Notes: Useful for long runs but not required. CLI logging is sufficient for v1.

---

## Out of Scope

### R030 — Human-in-the-Loop Agents
- Class: constraint
- Status: out-of-scope
- Description: No human player agents. All agents are LLM-controlled.
- Notes: Defines the study as multi-LLM, not human-LLM comparison.

### R031 — Non-Economic Game Variants
- Class: constraint
- Status: out-of-scope
- Description: Only Trade Island (resource trading, VP victory). No prisoner's dilemma variants, auctions, or other game types.
- Notes: Single domain = controlled comparison. Future work extends to other domains.

### R032 — Real-Time API (Streaming)
- Class: constraint
- Status: out-of-scope
- Description: All LLM calls are synchronous request/response. No streaming needed for simulation calls.
- Notes: Streaming adds complexity with no benefit for batch simulation.

---

## Coverage Summary

- **Active:** 12 requirements
- **Validated:** 0 (full validation pending Phase 0 + Phase 1 completion)
- **Partially validated:** 2 (R002, R011 — schema and engine proven; accepted-trade path and pipeline not yet)
- **Deferred:** 3
- **Out of scope:** 3
- **Total:** 18

## Traceability

| ID | Class | Status | Primary Owner | Validated |
|---|---|---|---|---|
| R001 | core-infrastructure | active | M001/S01 | M001/S01 ✅ |
| R002 | core-infrastructure | active | M001/S02 | M001/S02 partial — engine + schema ✅; accepted-trade path pending (D037) |
| R003 | performance-optimization | active | M001/S03 | unmapped |
| R004 | research-phase | active | M001/S04 | unmapped |
| R005 | research-phase | active | M002 | unmapped |
| R006 | research-phase | active | M003/S01 | unmapped |
| R007 | research-phase | active | M003/S02 | unmapped |
| R008 | research-phase | active | M003/S03 | unmapped |
| R009 | analysis | active | M004/S01 | unmapped |
| R010 | research-integrity | active | M001/S05 | unmapped |
| R011 | data-management | active | M001/S02 | M001/S02 partial — schema locked ✅; Polars pipeline pending (M002/S01) |
| R012 | output | active | M004/S02-S03 | unmapped |
| R020 | extensibility | deferred | — | — |
| R021 | extensibility | deferred | — | — |
| R022 | tooling | deferred | — | — |
| R030 | constraint | out-of-scope | — | — |
| R031 | constraint | out-of-scope | — | — |
| R032 | constraint | out-of-scope | — | — |
