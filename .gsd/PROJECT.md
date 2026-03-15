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

## Model Families

| ID | Model | Provider | Role |
|---|---|---|---|
| llama | Llama 3.3 70B | Groq | Agent |
| deepseek | DeepSeek V3.2 (chat) | DeepSeek API | Agent |
| deepseek-r | DeepSeek V3.2 (reasoner) | DeepSeek API | Reflection only |
| gemini | Gemini 2.5 Flash | Google AI Studio | Agent |
| mistral | Mistral Small 3.1 | Mistral La Plateforme | Agent + GM |

## Pre-Registered Hypotheses

- **H1:** Gini coefficient at round 25 differs across 4 families (Kruskal-Wallis, α=0.05)
- **H2:** Cross-model trade acceptance rate depends on pairing identity (logistic mixed-effects)
- **H3:** VP ratio deviates from 1.0 for ≥2 of 6 pairwise conditions
- **H4:** Architecture variance > persona variance on ≥3 of 5 metrics

## Budget

- Total API cost: ~$32 (₹2,700) for 335 games
- Hard cap: $80 via LiteLLM budget config
- Available budget: ₹12,500 ($148) — 55% utilization

## Deliverables

1. Paper (NeurIPS 2026 Workshop + AAMAS 2027 + arXiv)
2. `concordia-pairwise` — Open-source LiteLLM + Concordia v2.0 library
3. `model-pairwise-benchmark` — One-command benchmarking tool
4. `trade-island-dataset` — Full game logs on Hugging Face Datasets
5. Analysis notebooks (pre-registered, reproducible)
6. Blog/content (heatmaps, Twitter thread, findings narrative)

## Milestone Sequence

- 🔄 **M001: Infrastructure + Phase 0** — Setup, calibration, format ablation (30 games)
- ⬜ **M002: Phase 1 Monoculture** — 120 games, 4 model families × 30 games each
- ⬜ **M003: Phase 2 Pairwise + Persona** — 185 games (pairwise + 2B persona + 2C validation)
- ⬜ **M004: Analysis + Writing** — Full statistical analysis, figures, paper submission

## Architecture / Key Stack

```
LiteLLM (routing, cost tracking, retry, JSON mode, budget cap)
    ↕
Concordia v2.0 (simulation engine)
    ├── Simultaneous Engine (parallel agent actions)
    ├── Per-Agent LLM Override (pairwise support)
    ├── Trade Island Components (evaluate built-in marketplace first)
    ├── Prefix-First Prompt Templates (cache-optimized)
    ├── Checkpoint System (per-round state saves)
    └── Structured JSON Lines Logger
        ↓
Analysis: Polars, statsmodels, scikit-learn, NetworkX, sentence-transformers, seaborn
```

## Source of Truth

Blueprint: `research_blueprint_v6.md` in this directory. All decisions should be traceable to the blueprint. Deviations are recorded in `DECISIONS.md`.
