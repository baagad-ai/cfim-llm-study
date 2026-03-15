# Pairwise Behavioral Signatures: LLM Family Economic Simulation

**Paper:** *"Pairwise Behavioral Signatures: How Model Family Shapes Multi-Agent Economic Cooperation and Competition"*

Target: NeurIPS 2026 Foundation Models Workshop + AAMAS 2027 full paper

## What This Is

A controlled research study examining how model family (architecture + training) shapes multi-agent economic behavior. 6 LLM agents play "Trade Island" — a 25-round resource-trading game with VP-based victory — across 335 total games.

## Model Families

| Family | Model | Provider |
|---|---|---|
| Llama | Llama 3.3 70B | Groq |
| DeepSeek | DeepSeek V3.2 | DeepSeek API |
| Gemini | Gemini 2.5 Flash | Google AI Studio |
| Mistral | Mistral Small 3.1 | Mistral La Plateforme |

## Quick Start

```bash
# 1. Clone and enter project
cd research/model-family

# 2. Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Set API keys
cp .env.example .env
# Edit .env with your keys

# 5. Verify connectivity
python scripts/test_connectivity.py

# 6. Run a single calibration game
python scripts/run_game.py --model mistral --games 1 --phase 0
```

## Project Structure

```
research/model-family/
├── .gsd/               # GSD project management
├── config/             # LiteLLM config, game config
├── src/
│   ├── simulation/     # Trade Island + Concordia integration
│   ├── prompts/        # Cache-optimized prompt templates
│   ├── analysis/       # Pre-registered analysis scripts
│   └── scripts/        # Runner scripts
├── data/
│   ├── phase0/         # Calibration game logs
│   ├── phase1/         # Monoculture game logs (120 games)
│   └── phase2/         # Pairwise + persona + validation logs
├── notebooks/          # Analysis notebooks
├── tests/              # Unit + integration tests
├── requirements.txt
└── research_blueprint_v6.md  # Source of truth
```

## Research Phases

| Phase | Games | Purpose |
|---|---|---|
| Phase 0 | 30 | Calibration, format ablation, GM sensitivity |
| Phase 1 | 120 | Monoculture baselines (4 families × 30) |
| Phase 2 | 150 | Pairwise games (6 pairs × 25) |
| Phase 2B | 20 | Persona-vs-Architecture experiment |
| Phase 2C | 15 | Full-mix + temporal validation |
| **Total** | **335** | |

## Cost

- Total API budget: ~$32 (₹2,700)
- Hard cap: $80 via LiteLLM
- Available budget: ₹12,500 ($148)

## Pre-Registration

OSF registration: _[link will be added before Phase 1]_

## Reproducibility

All model versions pinned. All random seeds logged. Game logs include timestamps for temporal validation. Analysis scripts committed to OSF before data collection.

## Blueprint

See `research_blueprint_v6.md` for full research design, pricing, prompt templates, and experimental design. All decisions traced to the blueprint in `.gsd/DECISIONS.md`.
