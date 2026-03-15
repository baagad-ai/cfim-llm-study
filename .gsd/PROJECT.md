# Pairwise Behavioral Signatures — LLM Family Economic Simulation

## What This Is

A controlled research study examining how model family (architecture + training) shapes multi-agent economic behavior. Six LLM agents play "Trade Island" — a 25-round resource-trading game with VP-based victory — across 335 total games spanning monoculture, pairwise, persona-vs-architecture, and temporal validation conditions.

**Paper Title:** *"Pairwise Behavioral Signatures: How Model Family Shapes Multi-Agent Economic Cooperation and Competition"*

**Target Venues:**
- NeurIPS 2026 Foundation Models Workshop (September 2026 deadline) — short paper
- AAMAS 2027 (October 2026 deadline) — full paper
- Backup: AAAI 2027 (September 2026 deadline)

## Two Core Contributions

1. **First complete pairwise interaction matrix** of 4 model families in economic simulation, revealing matchup-specific cooperation, competition, and exploitation patterns invisible in monoculture studies
2. **Controlled persona-vs-architecture experiment** demonstrating model family drives more behavioral variation than prompt engineering

## Model Families (Actual Deployment — Updated from Blueprint)

| ID | Model | Provider | API Route | Role |
|---|---|---|---|---|
| llama | Llama 3.3 70B | Groq | `groq/llama-3.3-70b-versatile` | Agent |
| deepseek | DeepSeek V3 | OpenRouter | `openrouter/deepseek/deepseek-chat` | Agent |
| deepseek-r | DeepSeek R1 | OpenRouter | `openrouter/deepseek/deepseek-r1` | Reflection only |
| gemini | Gemini 2.5 Flash | Google AI Studio (paid) | `gemini/gemini-2.5-flash` | Agent |
| mistral | Mistral Small 2506 | Mistral La Plateforme | `mistral/mistral-small-2506` | Agent + GM |

**Note:** Direct DeepSeek API unavailable from India — using OpenRouter proxy (D019). Mistral version changed from 3.1-2503 to 2506 (D018).

## Pre-Registered Hypotheses

- **H1:** Gini coefficient at round 25 differs across 4 families (Kruskal-Wallis, α=0.05)
- **H2:** Cross-model trade acceptance rate depends on pairing identity (logistic mixed-effects)
- **H3:** VP ratio deviates from 1.0 for ≥2 of 6 pairwise conditions (t-test, BH-corrected)
- **H4:** Architecture variance > persona variance on ≥3 of 5 metrics (permutation test, seed=42)

Analysis stubs committed: commit `c4a9a1d` (2026-03-15), before any data collected.
OSF registration: pending (M001/S05 task — must complete before Phase 1).

## Budget

- Total API cost: ~$32 (₹2,700) for 335 games
- Hard cap: $80 via LiteLLM budget config
- Available budget: ₹12,500 ($148)
- Burned to date: $0.0008 (connectivity testing only)

## Current State

**Active milestone:** M001/S04 — Phase 0 Calibration (30 games) (next)
**Completed:** S01 (LiteLLM routing) ✅, S02 (Trade Island engine) ✅, S03 (Prompt Templates + Tolerant Parser) ✅
**Games completed:** 1 / 335 (1 calibration run — Mistral-mono, 25 rounds, $0.00)
**Cost burned:** $0.0008 / $80.00

## Deliverables

1. Paper (NeurIPS 2026 Workshop + AAMAS 2027 + arXiv)
2. `concordia-pairwise` — open-source LiteLLM + Concordia v2.0 library
3. `model-pairwise-benchmark` — one-command benchmarking tool
4. `trade-island-dataset` — full game logs on Hugging Face Datasets
5. Analysis notebooks (pre-registered, reproducible)
6. Blog/content (heatmaps, Twitter thread, findings narrative)

## Milestone Sequence

- 🔄 **M001: Infrastructure + Phase 0** — Setup, calibration, format ablation (30 games)
  - ✅ S01: LiteLLM + Environment (complete)
  - ✅ S02: Trade Island Engine (complete — custom loop, not Concordia; see D023)
  - ✅ S03: Prompt Templates + Tolerant Parser (complete — 23/23 tests pass; phase0 config real 4-family mix)
  - 🔄 S04: Phase 0 calibration games (next)
  - ⬜ S05: OSF pre-registration (blocks M002)
- ⬜ **M002: Phase 1 Monoculture** — 120 games (4 families × 30)
- ⬜ **M003: Phase 2 Pairwise + Persona** — 185 games
- ⬜ **M004: Analysis + Writing** — stats, figures, paper, open-source release

## Architecture / Stack

```
LiteLLM (routing, retry, cost tracking, budget cap)
    ├── Groq (Llama)          groq/llama-3.3-70b-versatile
    ├── OpenRouter (DeepSeek)  openrouter/deepseek/deepseek-chat
    ├── Google (Gemini)        gemini/gemini-2.5-flash  [thinking disabled]
    └── Mistral                mistral/mistral-small-2506
        ↕
Custom Simulation Loop — src/simulation/ (NOT Concordia — see D023)
    ├── GameConfig (Pydantic) — named configs: mistral-mono, phase0, pairwise-{A}-{B}
    ├── GameRunner — 25-round loop; flush-before-checkpoint ordering enforced
    ├── Agent — act(), respond_to_trade(), reflect() [rounds 5/10/15/20/25]
    ├── GM — sequential double-spend-safe trade validation (working-copy inventory)
    ├── GameLogger — line-buffered JSONL; fsync at checkpoints
    └── LLMRouter — per-provider kwargs; DeepSeek R1 reflection override; float cost guard
        ↓
scripts/run_game.py — CLI entry point (--config, --games); $80 BudgetManager cap
        ↓
data/raw/{game_id}/game.jsonl + checkpoint_r{N:02d}.json (25 per game)
        ↓
Analysis (S03+): Polars · statsmodels · scikit-learn · NetworkX · sentence-transformers · seaborn
```

## Source of Truth

Blueprint: `research_blueprint_v6.md`. All deviations in `.gsd/DECISIONS.md`.
