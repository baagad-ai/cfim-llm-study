# M001: Infrastructure + Phase 0 — Research

**Date:** 2026-03-15
**Scope:** S02 (Trade Island engine) through S05 (OSF pre-registration)

---

## Summary

S01 is complete and the foundation is solid. `litellm.drop_params = True`, all 4 providers verified, the `_hidden_params.response_cost` pattern for cost tracking is confirmed working (including with `mock_response` for tests). `gdm-concordia==2.4.0` is installed and the `LanguageModel` interface is verified: `sample_text(prompt: str)` only — no chat messages, no kwargs — which hard-confirms D023 (custom loop). The Concordia marketplace contrib component is a clearing-house (bids/asks queued over rounds), not bilateral bilateral proposal/accept — also confirmed unusable for Trade Island.

The critical discovery for S02 planning: the analysis stack (polars, statsmodels, scikit-learn, scipy, networkx, seaborn, sentence-transformers, pytest, jupyter) is **not installed**. The venv only has litellm, concordia, matplotlib, numpy, pandas, pydantic, tenacity, and supporting deps. This means `tests/test_smoke.py` cannot import polars or pytest without installing them first — and the analysis stubs (`h1-h4_*.py`) will fail to import at module load time. This must be resolved either in S02 (install dev/test deps) or treated as a known broken state with an install step in S03+. The `requirements.txt` lists the full stack but nothing enforces it was installed. **Candidate requirement: R013 — install verification step before first test run.**

The second notable finding: `.env.example` lists `DEEPSEEK_API_KEY` but the working code uses `OPENROUTER_API_KEY`. The `.env` has the right key (`OPENROUTER_API_KEY` is set). The example file is stale and misleading — fix it in S02 housekeeping.

**Primary recommendation:** Build `src/simulation/` as 6 focused modules (config, llm_router, agent, gm, game, logger) with plain litellm calls and dict-based inventory. Get a 3-round mock game running first (`mock_response=` in litellm), then switch to real APIs for the smoke test. Tenacity is installed but unnecessary — litellm's `num_retries` (via kwargs, confirmed working) is sufficient and avoids a dual-retry layering problem.

---

## Recommendation

Build a **200-line custom loop** calling `litellm.completion()` directly, using the exact call signatures already proven in `test_connectivity.py`. No Concordia entity/component system. Concordia is useful only as an import reference — `concordia.language_model.language_model.InvalidResponseError` is worth importing for typed exception handling, but that's the extent of it.

Module layout:
- `src/simulation/config.py` — game config dataclass + named configs (mistral-mono, phase0, etc.)
- `src/simulation/llm_router.py` — thin wrapper around `litellm.completion()` with per-provider call signatures
- `src/simulation/agent.py` — agent state + `decide()`, `respond_to_trade()`, `reflect()` methods
- `src/simulation/gm.py` — GM validation, building resolution, hunger application
- `src/simulation/game.py` — the 25-round orchestration loop + checkpoint read/write
- `src/simulation/logger.py` — JSONL event writer, structured schema

Start with mock tests (round-trip through all 6 modules with `mock_response=`), then run a single real game for smoke test.

---

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Per-provider retry + 429 handling | `litellm.completion(..., num_retries=3)` via kwargs (confirmed working) | Already tested; avoids dual-retry layering if we also use tenacity |
| Cost tracking per call | `response._hidden_params["response_cost"]` (confirmed working pattern in `test_connectivity.py`) | Accumulate in game loop; write to JSONL at game end |
| Gemini thinking disable | `thinking={"type": "disabled", "budget_tokens": 0}` (verified in S01) | D020 — confirmed working, `reasoning_tokens=None` |
| JSON fence stripping | `strip_md()` in `test_connectivity.py` (regex strips ` ```json ` fences) | Reuse directly — already handles Gemini's fallback behavior |
| Pydantic game config | `pydantic>=2.5` is installed | Use for config validation — catches misconfigured game specs early |
| Budget cap | `litellm.BudgetManager` (confirmed installed) | Set once, protects against runaway costs across multi-game runs |

---

## Existing Code and Patterns

- `scripts/test_connectivity.py` — **The reference implementation.** Contains: verified call signatures for all 4 providers, `strip_md()` JSON fence stripper, `_hidden_params["response_cost"]` cost tracking, `drop_params = True` pattern. Copy the provider call kwargs directly into `llm_router.py`.
- `config/litellm_config.yaml` — Authoritative per-provider kwargs, max_tokens, and pricing comments. Cross-reference when building `llm_router.py`.
- `src/analysis/h1_kruskal_wallis.py` — Defines the **JSONL schema contract**: `[game_id, model_family, round, agent_id, vp, inventory_value]`. The simulation's JSONL logger must emit these fields or the analysis stubs break. Check all 4 analysis stubs before finalizing the JSONL schema.
- `src/analysis/h4_architecture_vs_persona.py` — Imports `polars` and `numpy`. Will fail at import until polars is installed. Not a blocker for S02 but signals the install gap.
- `src/simulation/__init__.py` — Empty, ready for module exports.

---

## Constraints

- **Concordia `LanguageModel` interface is `sample_text(prompt: str)` only** — confirmed by direct inspection. No messages list, no kwargs for `thinking={}` or `response_format={}`. Cannot use Concordia's entity system without losing per-provider call control.
- **Concordia marketplace contrib is a clearing-house (bids/asks queued across rounds)** — not bilateral proposal/accept. Confirmed unusable for Trade Island's synchronous propose-then-respond mechanic.
- **`litellm.completion_cost()` requires full provider-prefixed model string** — `"groq/llama-3.3-70b-versatile"` not `"llama-3.3-70b-versatile"`. The `_hidden_params.response_cost` pattern sidesteps this correctly.
- **Analysis stack (polars, scipy, pytest, etc.) is not installed in `.venv/`** — `requirements.txt` lists them but they weren't installed in S01. `tests/test_smoke.py` cannot run without at minimum `pytest`. The analysis stubs will fail to import.
- **`litellm.drop_params = True` must be set globally at module load** — confirmed pattern in `test_connectivity.py`. If omitted, Gemini calls with `thinking={}` kwargs will raise `BadRequestError`.
- **`.env.example` lists `DEEPSEEK_API_KEY` but working env uses `OPENROUTER_API_KEY`** — stale example; actual key is correctly set. Fix `.env.example` in S02.
- **Concordia's `Inventory` component uses LLM chain-of-thought to infer inventory changes** — confirmed from source: it calls `sample_text()` with a reasoning prompt. Do NOT use it. Dict-based inventory is deterministic and correct for this domain.
- **DeepSeek R1 (reflection only) does not support JSON mode** — confirmed in `litellm_config.yaml`. Reflection output is free-form text. Parse with heuristic extraction or just store as-is.
- **`tenacity==9.1.4` is installed** — but using it on top of litellm's `num_retries` creates double-retry stacking. Choose one. Recommendation: rely solely on litellm's built-in retry for API calls; reserve tenacity for application-level retries (e.g., JSON parse failures up to N attempts with a fresh prompt).

---

## Common Pitfalls

- **Gemini `response_format={"type":"json_object"}` returns `content=None`** — D021 is confirmed. Do NOT add JSON mode to Gemini calls. Use `strip_md()` + tolerant parse. Symptom: `choices[0].message.content is None` with `finish_reason="length"`.

- **Inventory tracking via LLM inference** — Concordia's `Inventory` component calls the LLM to decide if a trade "caused a change" in inventory. This is non-deterministic and cannot be audited. Use a plain dict `{"wood":3,"stone":2,...}` and update it with verified arithmetic after each resolved trade.

- **Double-spending in concurrent trade proposals** — All 6 agents propose trades simultaneously. Without GM validation ordering, agent A can promise its last 2 wood to both B and C. The GM resolution step must validate trades in sequence against the *current* inventory (after prior trades in same round are applied), not the start-of-round snapshot. Lock the sequence in GM resolution prompt design.

- **DeepSeek R1 reflection token runaway** — R1's thinking chain can be long. `max_tokens=800` cap is specified in D024. Enforce this in `llm_router.py`'s reflection call path. Do not allow the general `max_tokens=150` default to apply to R1 calls.

- **Checkpoint file collision on resume** — If game crashes mid-round after writing the checkpoint but before flushing JSONL, the resume will re-run that round, producing duplicate JSONL events. Write JSONL first (or at end of round), then write checkpoint. Sequence matters.

- **`litellm.drop_params=True` must be module-level, not per-call** — Setting it locally in a function that imports litellm after another import has already configured it doesn't work. Set it once at the top of `llm_router.py` (and in any test entry point) before the first `litellm.completion()` call.

- **`mistral-small-2506` in config vs test scripts** — Verify the model string is `"mistral/mistral-small-2506"` (not `"mistral/mistral-small-latest"`) in every call site in `llm_router.py`. A stray `-latest` would break reproducibility and fail the D018 pin.

- **Analysis stubs import `polars` at module top** — Running `pytest` or importing `src.analysis` before polars is installed will fail with `ModuleNotFoundError: No module named 'polars'`. Install analysis deps before running any test that touches `src/analysis/`. The smoke test should only import `src/simulation/`.

- **`data/raw/{game_id}/` directory must be created before writing checkpoint** — The checkpoint pattern writes `data/raw/{game_id}/checkpoint_r{N:02d}.json`. `Path.mkdir(parents=True, exist_ok=True)` must precede the first write or it silently fails (or raises `FileNotFoundError` on macOS).

- **Game ID collisions** — If `game_id` is derived from config name + timestamp with second precision, two rapid test runs can produce the same ID and corrupt checkpoint files. Use `uuid.uuid4()[:8]` or add milliseconds.

---

## Open Risks

- **Phase 0 JSON parse rate below 90% on any model** — D012 says switch to verbose format. This would require re-running Phase 0 for affected models and adds ~$0.50 extra. Not a blocker, but the verbose fallback path needs to be wired before Phase 0 starts (S03/S04 boundary).

- **Gemini 429 burst during Phase 0 format ablation** — 80 calls in quick succession to `gemini-2.5-flash` on paid tier. Paid tier has higher RPM limits but not unlimited. LiteLLM retry handles transient 429s, but a sustained burst could exhaust retries. Add a `time.sleep(0.5)` inter-call gap during format ablation (same pattern as `test_connectivity.py`).

- **DeepSeek R1 cost in Phase 0** — 30 games × 5 reflections × R1 = 150 R1 calls for DeepSeek-monoculture games. At $0.55/$2.19 and 800 token cap, worst case ~$0.26/game reflection cost. Phase 0 has 30 games — if most are DeepSeek mono, this could approach $8. Not the $0.45 estimate in D024. Monitor carefully and potentially limit R1 calls to Phase 1+ (use V3.2 for Phase 0 reflection).

- **`sentence-transformers` install time** — Not installed; requires torch (~1.5GB). Install should happen before Phase 0 analysis but torch install on Python 3.14 may have compatibility issues. Verify separately before S03 or S04.

- **No `tests/` directory exists yet** — `pyproject.toml` points `testpaths = ["tests"]` but the directory doesn't exist. `pytest` will either error or silently pass. Create `tests/` with `test_smoke.py` in S02.

- **`data/raw/` structure mismatch with analysis stubs** — The JSONL schema is not finalized. The analysis stubs define expected columns (`game_id, model_family, round, agent_id, vp, inventory_value`) but the logger hasn't been built yet. If the logger emits different column names, all 4 pre-registered analysis scripts break. Finalize and document the schema in S02 before writing a single production event.

---

## Requirements Analysis (Against Active Requirements)

| Req | Assessment |
|-----|-----------|
| R001 (LiteLLM routing) | ✅ Complete — S01 verified |
| R002 (Trade Island engine) | ⬜ Core S02 work — no code yet |
| R003 (Cache-optimized prompts) | ⬜ S03 — prefix-first structure is designed (blueprint §2.2-2.5), not coded |
| R004 (Phase 0) | ⬜ S04 — blocked on R002 + R003 |
| R010 (OSF pre-registration) | ⬜ S05 — blocked on R002 (analysis stubs must reference final JSONL schema) |
| R011 (JSONL logging) | ⬜ S02 — schema not finalized; analysis stubs define partial contract |

**Candidate requirements surfaced by research:**
- **R013 (Candidate):** Install verification step — before first test run, verify all `requirements.txt` packages are installed. `pip install -r requirements.txt` must be idempotent and documented. The current venv gap (missing polars, pytest, scipy, etc.) will cause silent test failures.
- **R014 (Candidate):** `.env.example` accuracy — `DEEPSEEK_API_KEY` should be `OPENROUTER_API_KEY`. This is a minor fix but a new contributor following the example would waste time.

Both are small scope — R013 is advisory (an install step note in README suffices); R014 is a 1-line fix.

---

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| LiteLLM | No dedicated skill found | none found |
| Concordia | No dedicated skill found | none found |
| General research/simulation Python | `systematic-debugging` (installed) | installed — use if game loop shows unexpected behavior |

---

## Sources

- Concordia `LanguageModel` interface: `/Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family/.venv/lib/python3.14/site-packages/concordia/language_model/language_model.py` — `sample_text(prompt: str)` only, no messages/kwargs
- Concordia marketplace contrib: `.venv/.../concordia/contrib/components/game_master/marketplace.py` — clearing-house (bids/asks), not bilateral
- Concordia Inventory component: `.venv/.../concordia/components/game_master/inventory.py` — uses `sample_text()` chain-of-thought for inventory inference; do not use
- LiteLLM version and cost tracking: confirmed `litellm==1.82.2`, `_hidden_params["response_cost"]` pattern works (source: `scripts/test_connectivity.py`, runtime verification)
- Installed packages: `pip list` in `.venv/` — polars, scipy, statsmodels, scikit-learn, networkx, seaborn, pytest all missing
- JSONL schema contract: `src/analysis/h1_kruskal_wallis.py` comment: `[game_id, model_family, round, agent_id, vp, inventory_value, ...]`
- `.env` key names: `OPENROUTER_API_KEY` is set (not `DEEPSEEK_API_KEY` as `.env.example` states)
- DeepSeek R1 no-JSON-mode constraint: `config/litellm_config.yaml` — `deepseek-reasoner` has no `response_format` entry
