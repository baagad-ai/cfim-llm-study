# S02: Trade Island Engine — Research

**Date:** 2026-03-15
**Scope:** R002 (Trade Island engine), R011 (JSONL logging schema)

---

## Summary

S01 left a clean, verified foundation: all 4 providers are confirmed working, per-provider call signatures are locked in `test_connectivity.py`, and `litellm.drop_params = True` is the established pattern. The `src/simulation/__init__.py` is empty and `tests/` and `data/raw/` directories exist (empty). No `pytest`, `polars`, or `scipy` is installed — `tests/test_smoke.py` will need them as T01's first action.

The core architectural decision (D023 — custom loop) is already settled and confirmed correct. `gdm-concordia==2.4.0` is installed, but `concordia.language_model.LanguageModel` is `sample_text(prompt: str)` only — per-provider chat kwargs cannot route through it. There is **no evaluation needed**; the S02-concordia-trade-island.md sketch's T02 (marketplace evaluation gate) is eliminated per D026.

The JSONL schema is the critical boundary contract for S03 and both pre-registered analysis stubs that use column names (`h1`: `game_id, model_family, round, agent_id, vp`; `h2`: `game_id, round, proposer_model, responder_model, pairing, give_resource, want_resource, accepted`). These column names must be emitted exactly — they are locked in the pre-registered stubs and cannot be changed without breaking OSF integrity.

One fresh pitfall surfaced in research: `litellm.completion(mock_response=...)` returns `_hidden_params["response_cost"]` as `None` (not `0.0`). Cost accumulation in the game loop must guard with `cost = result._hidden_params.get("response_cost") or 0.0` — not `or 0`. Any test that checks `total_cost == 0.0` will silently pass a `None` accumulation bug.

**Primary recommendation:** Build the 6 modules in strict dependency order: `config.py` → `logger.py` → `llm_router.py` → `agent.py` → `gm.py` → `game.py`. Install deps first (T01), wire mock-response tests before any real API call, then run the smoke test. Keep `game.py` under 250 lines by pushing phase logic into `gm.py` and `agent.py`.

---

## Recommendation

Build `src/simulation/` as 6 focused modules calling `litellm.completion()` directly. No Concordia entity system. Full plan:

1. **T01 — Install deps:** `pip install pytest polars scipy statsmodels scikit-learn networkx seaborn sentence-transformers jupyter` → then `pip freeze > requirements-lock.txt`. Verify `import pytest; import polars` before any test work.

2. **T02 — config.py + logger.py:** These have zero external LLM dependencies — write them first, test them with plain `assert` before `pytest` exists. Get the JSONL schema committed in code before any other module uses it.

3. **T03 — llm_router.py:** Exact copy of per-provider call signatures from `test_connectivity.py`. The only new logic is the model-routing table (agent_id → provider config) and the R1 reflection override for DeepSeek agents.

4. **T04 — agent.py + gm.py:** Agent wraps `llm_router.py`; GM uses Mistral with JSON mode. Both call `litellm.completion()` directly. GM double-spend prevention is the highest-risk logic — test it in isolation with mock responses covering the collision case.

5. **T05 — game.py + run_game.py:** 25-round orchestration. Write checkpoint before flushing JSONL (see pitfall below). ID collision prevention via `uuid4()`.

6. **T06 — smoke test:** Run `python scripts/run_game.py --config mistral-mono --games 1`. Verify cost ≤$0.02, 25 rounds, ≥1 accepted trade.

The 6-module decomposition is straightforward — the design is already fully specified. The only non-obvious decisions are in the GM resolution ordering and checkpoint/JSONL write sequence.

---

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Per-provider retry + 429 backoff | `litellm.completion(..., num_retries=3)` via `**kwargs` — confirmed accepted | Already tested; avoids dual-retry layering if tenacity also wraps it |
| Cost tracking per call | `r._hidden_params.get("response_cost") or 0.0` — confirmed working in `test_connectivity.py` | Guard `or 0.0` not `or 0` — mock calls return `None` not `0` |
| Gemini thinking disable | `thinking={"type": "disabled", "budget_tokens": 0}` in every Gemini call | D020 confirmed; omitting it causes reasoning token leakage at 200-token ceiling |
| JSON fence stripping | `strip_md()` in `test_connectivity.py` — 3-line regex | Reuse verbatim; do NOT reinvent |
| Pydantic config validation | `pydantic>=2.12.5` installed | Catches misconfigured game specs before round 1 |
| Unique game IDs | `uuid.uuid4().hex[:8]` | Second-granularity timestamps collide on rapid test reruns |
| Budget cap | `litellm.BudgetManager` — importable, confirmed | Set $80 hard cap once at game runner startup |

---

## Existing Code and Patterns

- `scripts/test_connectivity.py` — **The reference implementation.** Per-provider kwargs to copy verbatim into `llm_router.py` (lines 17-42). `strip_md()` function to copy verbatim. Cost tracking pattern. `litellm.drop_params = True` at module top. `time.sleep(0.5)` inter-call gap pattern.

- `src/analysis/h1_kruskal_wallis.py` — Defines column contract: `[game_id, model_family, round, agent_id, vp]`. Uses `pl.col("round") == 25` to filter. The logger's `round_end` event must emit exactly these names. Pre-registered — cannot be changed.

- `src/analysis/h2_logistic_mixed_effects.py` — Defines trade event contract: `[game_id, round, proposer_model, responder_model, pairing, give_resource, want_resource, accepted]`. The `trade_response` and `gm_resolution` events must emit these fields for Phase 2 analysis.

- `config/litellm_config.yaml` — Authoritative per-provider model strings and `max_tokens` defaults. `deepseek-reasoner` has `max_tokens: 300` (not 150); R1 reflection calls must use 800 as per D024.

- `src/simulation/__init__.py` — Empty. Will hold module-level exports after all 6 modules are written.

---

## JSONL Schema (Locked S02 → S03 Boundary Contract)

Every event line has mandatory fields: `ts` (ISO8601), `event` (string), `round` (int).

| event | required fields | analysis consumer |
|-------|----------------|-------------------|
| `game_start` | `game_id, config, model_assignments, seed` | metadata |
| `round_start` | `round` | — |
| `agent_action` | `agent_id, model_family, action_type, target, give, want` | — |
| `trade_proposal` | `round, from_agent, to_agent, give_resource, give_qty, want_resource, want_qty, proposer_model` | H2 |
| `trade_response` | `round, from_agent, to_agent, accepted, counter, responder_model` | H2 |
| `gm_resolution` | `round, trade_idx, valid, reason, proposer_model, responder_model, pairing, give_resource, want_resource, accepted` | H2 |
| `build` | `round, agent_id, model_family, building, vp_delta` | — |
| `grain_consumption` | `round, agent_id, grain_before, grain_after, damage` | — |
| `reflection` | `round, agent_id, model_family, summary, model_used` | — |
| `round_end` | `round, vp_state: {agent_id: int}, inventories: {agent_id: {res: int}}, agent_id (per-row)` | **H1** — `game_id, model_family, round, agent_id, vp` |
| `game_end` | `game_id, winner, final_vp, rounds_played, total_cost_usd` | — |

**H1 note:** The analysis loads round_end events and expects `game_id`, `model_family`, `round`, `agent_id`, `vp` as flat columns. Either emit one line per agent per round_end, or ensure the analysis loader explodes the `vp_state` dict. Emitting one line per agent is simpler and keeps the schema flat — choose that.

**H2 note:** `pairing` field is only meaningful in pairwise games (format: `"llama_mistral"`). In monoculture games, `pairing` = `model_family + "_mono"` to avoid nulls.

---

## Constraints

- `concordia.language_model.LanguageModel.sample_text(prompt: str)` — text only, no messages, no chat kwargs. Cannot bridge per-provider workarounds through it. Do not use.
- `concordia.contrib.components.game_master.marketplace` — clearing-house (bids/asks as `Order` objects queued across rounds). Not bilateral proposal/respond. Do not use.
- `concordia.components.game_master.inventory.Inventory` — uses `sample_text()` chain-of-thought to infer inventory changes from natural language events. Non-deterministic, cannot be audited. Do not use — plain dict.
- `litellm.drop_params = True` must be set at module level in `llm_router.py` before any call. Per-function setting does not reliably catch all cases.
- `mistral/mistral-small-2506` — not `mistral-small-latest`. Every call site in `llm_router.py` must use the pinned string (D018).
- `gemini/gemini-2.5-flash` calls require `thinking={"type": "disabled", "budget_tokens": 0}` AND `max_tokens=200` minimum — both together (D020, D022).
- `openrouter/deepseek/deepseek-r1` for DeepSeek reflection only. `max_tokens=800` cap for R1. No JSON mode for R1 — reflection output is free text.
- `tests/` directory exists but is empty. `data/raw/` directory exists and is empty.
- `pytest`, `polars`, `scipy`, `statsmodels`, `scikit-learn`, `networkx`, `seaborn`, `sentence-transformers` are **NOT installed**. T01 must install them before any test work.
- `tenacity==9.1.4` is installed but creates dual-retry stack if used alongside `num_retries=3`. Use tenacity only for application-level retries (e.g., JSON parse retry up to 3 attempts with a new prompt call).

---

## Common Pitfalls

- **`mock_response` cost is `None`, not `0.0`** — `r._hidden_params.get("response_cost")` returns `None` for mock calls. Cost accumulation must be `total_cost += (r._hidden_params.get("response_cost") or 0.0)`. A bare `or 0` will silently accumulate `None` values and crash at the final sum.

- **GM double-spend: snapshot vs sequential validation** — All 6 agents propose trades simultaneously. If GM validates all proposals against the same start-of-round snapshot, agent A can promise its last 2 wood to both B and C (both proposals validate as "ok"). GM must process trade 1 → update inventories in a working copy → validate trade 2 against the updated copy → repeat sequentially. The prompt must pass the *current working-copy* inventory to the GM for each subsequent trade in the batch.

- **Checkpoint write ordering** — Write JSONL events for the round FIRST, then write the checkpoint file. If the process crashes between checkpoint write and JSONL flush, resume re-runs the round with the checkpoint's state, producing duplicate events. Correct sequence: append all round events to JSONL → fsync → write checkpoint JSON.

- **`data/raw/{game_id}/` parent directory** — `Path.mkdir(parents=True, exist_ok=True)` before the first write. `data/raw/` exists but `data/raw/{game_id}/` does not.

- **Game ID collision** — Two rapid test runs within the same second produce identical IDs if using `config+timestamp`. Use `uuid.uuid4().hex[:8]` for the suffix.

- **DeepSeek R1 `max_tokens` override** — `config/litellm_config.yaml` has `deepseek-reasoner` at `max_tokens: 300`. D024 requires `max_tokens=800` for reflection. `llm_router.py` must override the config default for R1 reflection calls specifically. The YAML is a reference, not a live router in this custom-loop architecture.

- **Analysis stubs fail to import** — `src/analysis/h1_kruskal_wallis.py` imports `polars` at module top. Running `pytest` or any test that touches `src.analysis` before polars is installed will fail with `ModuleNotFoundError`. `test_smoke.py` must only import `src.simulation.*`, not `src.analysis.*`.

- **`vp` field naming** — H1 analysis filters on `pl.col("vp")`. The round_end log line must use `"vp"` as the key, not `"victory_points"` or `"score"`. Verify the field name matches before the smoke test is run.

- **Reflection model string for DeepSeek** — The reflection call for DeepSeek agents uses `openrouter/deepseek/deepseek-r1`, not `openrouter/deepseek/deepseek-chat`. The router must switch model string for `reflect()` calls, not just pass kwargs differently.

- **`tenacity` version** — `requirements.txt` specifies `>=8.2.0,<9.0.0` but installed version is `9.1.4`. If tenacity is used, confirm API compatibility with v9 before calling. The retry decorator signature changed between v8 and v9.

---

## Open Risks

- **GM JSON parse failure rate** — The GM resolution prompt is the most complex call (~120 tokens input, structured list of trades). If Mistral returns malformed JSON for multi-trade rounds, the game hangs. Need a fallback: if GM response fails to parse after 2 retries, log the failure event and mark all trades in the batch as invalid (safe conservative resolution). This must be wired in S02, not deferred.

- **`sentence-transformers` install on Python 3.14** — Not installed. Requires `torch` (~1.5GB). Python 3.14 compatibility with torch wheels is uncertain as of March 2026. This is not a blocker for S02 (smoke test doesn't need it) but needs a separate verification before Phase 0 analysis runs. Flag for S03/S04 boundary check.

- **Blueprint v6 pricing vs actual** — Blueprint §1 notes DeepSeek unified pricing ($0.28/$0.42 for both V3.2 and R1). The DECISIONS.md D024 contradicts this ($0.55/$2.19 for R1). Pricing may have changed between blueprint writing (March 2026) and actual. The `_hidden_params["response_cost"]` pattern captures actual billed cost — trust that at runtime; don't hardcode cost estimates in the game loop.

- **Round ordering: reflection frequency** — Blueprint §2.5 specifies reflection every 5 rounds (rounds 5, 10, 15, 20, 25 = 5 reflections). Reflection must happen *after* round_end state is logged (so the agent has current inventory/VP context). If reflection fires before round_end, the summary is stale. Phase ordering in `game.py` must be: phases 1-5 → round_end log → reflection if round % 5 == 0 → checkpoint.

- **Mistral GM confound** — Using Mistral as GM in a Mistral-monoculture smoke test conflates two things. The GM resolution prompt expects JSON `{"valid":[bool,...],"reason":[...]}`. If the GM model and agent model are both Mistral, a bug in the prompt might be masked by Mistral's instruction following. Consider running the smoke test once with a fixed mock GM (no LLM call, all trades auto-valid) to isolate agent behavior from GM behavior, then a second run with real GM.

---

## Skill Discovery

| Technology | Skill | Status |
|------------|-------|--------|
| LiteLLM | No dedicated skill found | none found |
| Concordia | No dedicated skill found | none found |
| Game loop / simulation Python | `systematic-debugging` | installed — use if smoke test behavior is unexpected |

---

## Sources

- Concordia `LanguageModel` interface: `.venv/.../concordia/language_model/language_model.py` — `sample_text(prompt: str)` only, `sample_choice()` for multiple-choice; no messages/kwargs. Custom loop required (D023 confirmed).
- Concordia `Inventory` component source — uses `sample_text()` CoT to infer changes from natural language. Non-deterministic. Do not use.
- Concordia `marketplace` contrib source — `Order` dataclass with bid/ask/round fields; not bilateral proposal/respond. Do not use.
- `concordia.contrib.language_models` — has groq, google, mistral, openai wrappers, but all wrap `sample_text()` interface. Cannot pass chat-mode kwargs.
- `gdm-concordia==2.4.0` confirmed via `importlib.metadata.version('gdm-concordia')`
- `litellm==1.82.2` — `mock_response` accepted via `**kwargs`; `num_retries=3` accepted via `**kwargs`; `_hidden_params["response_cost"]` returns `None` for mock calls (not `0.0`)
- Installed packages verified: `polars`, `pytest`, `scipy`, `statsmodels`, `scikit-learn`, `networkx`, `seaborn`, `sentence-transformers` all **absent** from `.venv/`
- H1 analysis stub column contract: `[game_id, model_family, round, agent_id, vp]` — `src/analysis/h1_kruskal_wallis.py` docstring
- H2 analysis stub column contract: `[game_id, round, proposer_model, responder_model, pairing, give_resource, want_resource, accepted]` — `src/analysis/h2_logistic_mixed_effects.py` docstring
- `tests/` and `data/raw/` directories exist (empty) — created during S01 scaffold
- `.env` keys present: `GROQ_API_KEY`, `GOOGLE_API_KEY`, `MISTRAL_API_KEY`, `OPENROUTER_API_KEY`
