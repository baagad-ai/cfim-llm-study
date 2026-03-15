# Cross-Family Interaction Matrix (CFIM)
*How LLM Behavioral Profiles Shift as a Function of Opponent Model Family*

**Status:** Active — M001 executing (S01 T01 complete)
**Target venues:** AAMAS 2027 full paper · NeurIPS 2026 Foundation Models workshop (short paper)
**Design doc:** `.gsd/SIMULATION_DESIGN.md` (authoritative — all implementation follows this)
**Last updated:** 2026-03-15

---

## The Claim

LLM cooperation profiles are not fixed traits — they are opponent-contingent responses. The same model family behaves measurably differently facing a same-family opponent versus a cross-family opponent. These relational response patterns form a stable, reproducible N×N matrix (the CFIM) that serves as a richer behavioral characterization than any single-condition cooperation rate.

---

## Two-Study Structure

**Study 1 (Primary): CFIM via Repeated Negotiated Exchange (RNE)**
- 2-agent dyadic bilateral trading game, 35 rounds per session
- 7 model families × 7 families = 28 unique pairs (upper triangle)
- 3 game conditions (A: coordination, B: mixed-motive, C: asymmetric power)
- 2 disclosure sub-conditions (blind / disclosed)
- 3 prompt framings (neutral / social / strategic)
- 20 sessions per cell → 3,360 total sessions
- Measures M1–M6 (cooperation rate, exploitation delta, adaptation lag, betrayal recovery, min acceptable offer, identity sensitivity)

**Study 2 (Ecological validity): Harbour 6-agent game**
- Tests whether CFIM bilateral patterns predict multi-agent dynamics
- Mono + mixed compositions designed from Study 1 findings
- ~80 games

---

## Model Families (7 — Claude Haiku excluded, budget constraint)

| ID | Model | Provider | Route |
|---|---|---|---|
| llama | Llama 3.3 70B | Groq | `groq/llama-3.3-70b-versatile` |
| deepseek | DeepSeek V3 | OpenRouter | `openrouter/deepseek/deepseek-chat` |
| gemini | Gemini 2.5 Flash | Google | `gemini/gemini-2.5-flash` |
| mistral | Mistral Small 2506 | Mistral | `mistral/mistral-small-2506` |
| gpt4o-mini | GPT-4o mini | OpenAI | `openai/gpt-4o-mini` |
| qwen | Qwen 2.5 72B | Together.ai | `together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo` |
| phi4 | Phi-4 | Together.ai | `together_ai/microsoft/phi-4` |

---

## Pre-Registered Hypotheses (H1–H5)

- **H1 — Self-play premium:** Diagonal CFIM cells > off-diagonal (Wilcoxon signed-rank)
- **H2 — Pairing identity predicts cooperation:** Mixed-effects logistic model LRT p<0.05
- **H3 — Disclosure amplifies divergence:** |M6| > 0, larger for cross-family pairs (two-sided)
- **H4 — Adaptation lag is pair-specific:** Kruskal-Wallis across 28 pairs, η²>0.10
- **H5 — CFIM predicts multi-agent outcomes:** Study 2 VP variance ~ bilateral M1, R²>0.15

Analysis stubs: `src/analysis/h1_self_play_premium.py` through `h5_cfim_to_multiagent.py`
Pre-registration: `docs/osf_preregistration.md` (OSF submission pending — M001/S05)

---

## Budget

| Phase | Sessions | Est. cost |
|---|---|---|
| Phase 0 calibration (4 families, 10 sessions × 3 conditions × 2 disclosure) | 240 | ~$11 |
| Study 1 full CFIM (28 pairs × 120 sessions) | 3,360 | ~$47 |
| Study 2 Harbour (~80 games) | 80 | ~$15 |
| **Total** | | **~$73** |

Hard cap: $80 via LiteLLM budget config. Buffer: $7.

---

## Milestone Sequence

- 🔄 **M001: RNE Engine + Phase 0** — Build Study 1 engine, run 240 Phase 0 sessions, OSF register
- ⬜ **M002: Study 1 Full CFIM** — 3,360 sessions across 28 pairs × 3 conditions × 2 disclosure × 3 framings
- ⬜ **M003: Study 2 Harbour** — 80 games, ecological validity bridge
- ⬜ **M004: Analysis + Writing** — CFIM matrix, H1–H5 tests, paper, open-source

---

## Current State

- **Completed infrastructure:** LiteLLM routing (7 families), `RNEConfig`, `GameLogger`, `call_llm`, `PROVIDER_KWARGS`, full RNE engine (35-round loop, M1–M4 metrics, perturbation), `src/prompts/rne_prompts.py` (9 system prompt variants, disclosure injection, 4-strategy tolerant parser), `scripts/run_rne.py` CLI
- **S01 complete:** RNE engine + router (T01–T03 done; T04 run_rne.py pending — covered by S02/T03)
- **S02 complete:** Prompt architecture — `build_system_prompt`, `build_round_messages`, `parse_rne_response`. 165 tests pass. Real Mistral×Llama smoke run: $0.0072/session ≤ $0.05.
- **S04 partial:** OSF pre-registration docs + analysis stubs committed. Formal OSF submission pending (human action).
- **Pending M001:** Phase 0 calibration (240 sessions), OSF formal submission
- **Games completed:** ~3 Study 1 smoke sessions / 3,360 target
- **Cost burned:** ~$20 (infrastructure + calibration experiments, S01–S04 prior work + S02 smoke runs)

## Architecture

```
LiteLLM (routing · retry · cost guard · drop_params)
  └── 7 providers: Groq · OpenRouter · Google · Mistral · OpenAI · Together.ai(×2)
        ↕
src/simulation/
  rne_game.py       — Study 1: 35-round bilateral RNE engine (T02, in progress)
  harbour_game.py   — Study 2: 6-agent Harbour (M001/S04+)
  config.py         — RNEConfig (7-family validated) · GameConfig · _MODEL_REGISTRY
  llm_router.py     — call_llm(family) → litellm response · 7-family PROVIDER_KWARGS
  logger.py         — GameLogger · line-buffered JSONL · data/study1/{session_id}/
src/prompts/
  rne_prompts.py    — build_system_prompt (9 LRU-cached) · build_round_messages (disclosure) · parse_rne_response (4-strategy)
  json_utils.py     — tolerant parser · get_completion_kwargs
src/analysis/
  h1_self_play_premium.py … h5_cfim_to_multiagent.py  (pre-registered stubs)
scripts/
  run_rne.py        — Study 1 CLI (implemented, smoke-verified)
  run_harbour.py    — Study 2 CLI (M001/S04+)
  run_phase0.py     — Phase 0 calibration CLI (M001/S03+)
```

## Source of Truth

Design: `.gsd/SIMULATION_DESIGN.md`
Decisions: `.gsd/DECISIONS.md` (D001–D060)
Requirements: `.gsd/REQUIREMENTS.md`
