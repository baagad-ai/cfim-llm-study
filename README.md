# Cross-Family Interaction Matrix (CFIM)
### Opponent-Contingent Behavioral Profiles in LLM Agents

> **Pre-registration:** OSF — _link added before Phase 1 data collection_
>
> **Target venues:** AAMAS 2027 (full paper) · NeurIPS 2026 Foundation Models Workshop (short paper)

---

## The Claim

LLM cooperation profiles are not fixed traits — they are **opponent-contingent responses**. The same model family behaves measurably differently when facing a same-family opponent versus a cross-family opponent. These relational response patterns form a stable, reproducible N×N matrix (the **CFIM**) that serves as a richer behavioral characterisation than any single-condition cooperation rate.

---

## Study Design

### Study 1 — Repeated Negotiated Exchange (RNE)

Two-agent bilateral trading game, 35 rounds per session.

| Dimension | Values |
|---|---|
| Model families | 7 (Llama, DeepSeek, Gemini, Mistral, GPT-4o-mini, Qwen, Phi-4) |
| Unique pairs | 28 (upper triangle of 7×7) |
| Game conditions | A: coordination · B: mixed-motive · C: asymmetric power |
| Disclosure | blind · disclosed |
| Prompt framing | neutral · social · strategic |
| Sessions per cell | 20 |
| **Total sessions** | **3,360** |

**Measures:** M1 cooperation rate · M2 exploitation delta · M3 adaptation lag · M4 betrayal recovery · M5 min acceptable offer · M6 identity sensitivity

### Study 2 — Harbour 6-Agent Game (Ecological Validity)

Tests whether CFIM bilateral patterns predict multi-agent outcomes across mono and mixed model compositions (~80 games).

---

## Pre-Registered Hypotheses

| ID | Hypothesis | Test |
|---|---|---|
| H1 | Self-play premium: diagonal CFIM cells > off-diagonal | Wilcoxon signed-rank |
| H2 | Pairing identity predicts cooperation | Mixed-effects logistic LRT p < 0.05 |
| H3 | Disclosure amplifies cross-family divergence | \|M6\| > 0, two-sided |
| H4 | Adaptation lag is pair-specific | Kruskal-Wallis η² > 0.10 |
| H5 | CFIM predicts multi-agent outcomes | Study 2 VP variance ~ M1, R² > 0.15 |

Analysis stubs: `src/analysis/h1_*` through `src/analysis/h5_*` — committed before any Phase 1 data collection.

---

## Model Families

| ID | Model | Provider |
|---|---|---|
| `llama` | Llama 3.3 70B | Groq |
| `deepseek` | DeepSeek V3 | OpenRouter |
| `gemini` | Gemini 2.5 Flash | Google |
| `mistral` | Mistral Small 2506 | Mistral |
| `gpt4o-mini` | GPT-4o mini | OpenAI |
| `qwen` | Qwen 2.5 72B | Together.ai |
| `phi4` | Phi-4 | Together.ai |

---

## Repository Structure

```
cfim-llm-study/
├── src/
│   ├── simulation/         # RNE game engine + LLM router
│   ├── prompts/            # Prompt templates (9 system-prompt variants, parser)
│   └── analysis/           # Pre-registered analysis stubs H1–H5
├── scripts/
│   ├── run_rne.py          # Main session runner
│   └── run_format_ablation.py
├── tests/                  # Unit + integration tests (165 passing)
├── docs/
│   └── osf_preregistration.md   # Full pre-registration document
├── data/
│   └── metadata/           # OSF registration JSON (no raw game data in repo)
├── config/                 # LiteLLM + game config
├── .env.example            # API key template
├── requirements.txt
└── pyproject.toml
```

> **Raw game data** (JSONL session logs) are not stored in this repository due to size.
> All data will be deposited on OSF/Zenodo alongside the paper.

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/baagad-ai/cfim-llm-study
cd cfim-llm-study

# 2. Environment
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 3. API keys
cp .env.example .env
# Fill in keys for Groq, Mistral, Google, OpenRouter (DeepSeek)

# 4. Smoke test (mock mode — no API calls)
pytest tests/ -v

# 5. Single real session
python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1
```

---

## Reproducibility

- All model versions pinned in `requirements.txt`
- All random seeds logged per session in `summary.json`
- Game logs (JSONL) include round-level events for full audit trail
- Analysis stubs H1–H5 committed and OSF-registered before Phase 1 data collection
- Format decisions locked per model family (see `DECISIONS.md`)

---

## Cost Estimate

| Phase | Sessions | Est. Cost |
|---|---|---|
| Phase 0 calibration | 30 | ~$0.75 |
| Phase 1 (Study 1 full) | 3,360 | ~$85 |
| Phase 2 (Study 2) | ~80 | ~$8 |

Hard budget cap enforced via LiteLLM proxy.

---

## Citation

_Pre-print and citation to be added after Phase 1 completion._

---

## License

Code: MIT. Data and paper: CC BY 4.0.
