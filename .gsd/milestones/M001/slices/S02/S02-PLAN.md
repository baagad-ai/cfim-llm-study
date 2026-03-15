# S02: Trade Island Engine

**Goal:** Build the 6 `src/simulation/` modules and `scripts/run_game.py` so that a complete 25-round game runs end-to-end, writes valid JSONL, and costs ≤$0.02 — with no double-spend possible and crash-resume verified.
**Demo:** `python scripts/run_game.py --config mistral-mono --games 1` completes, `data/raw/{game_id}/game.jsonl` exists with ≥25 `round_end` events, ≥1 `gm_resolution` with `accepted=true`, and `game_end.total_cost_usd ≤ 0.02`. `pytest tests/test_smoke.py` passes with stubbed LLM.

## Must-Haves

- `src/simulation/config.py` — `GameConfig` dataclass + named configs (`mistral-mono`, `phase0`, `pairwise-{A}-{B}`) with Pydantic validation
- `src/simulation/logger.py` — JSONL writer; flat `round_end` lines emitting `game_id, model_family, round, agent_id, vp` (exact field names, one line per agent)
- `src/simulation/llm_router.py` — per-provider routing with DeepSeek R1 override for reflection; `mock_response` cost guard (`or 0.0` not `or 0`); `litellm.drop_params = True` at module level
- `src/simulation/agent.py` — wraps `llm_router.py`; interprets action JSON; calls `reflect()` on rounds 5/10/15/20/25 *after* `round_end` is logged
- `src/simulation/gm.py` — sequential double-spend-safe trade validation; JSON parse fallback (all-invalid) after 2 retries; emits `gm_resolution` events with all H2 columns
- `src/simulation/game.py` — 25-round loop; JSONL flush → fsync → checkpoint ordering (this order, not reversed)
- `scripts/run_game.py` — CLI with `--config` and `--games` args; `uuid4().hex[:8]` game IDs; `data/raw/{game_id}/` mkdir on first write
- `tests/test_smoke.py` — 3-round mock game with `mock_response=...`; validates schema, double-spend prevention, cost accumulation, checkpoint file existence

## Proof Level

- This slice proves: integration — real LiteLLM calls to Mistral with actual game state
- Real runtime required: yes (T04 smoke run hits Mistral API)
- Human/UAT required: no

## Verification

- `pytest tests/test_smoke.py` — all tests pass (3-round mock game, schema assertions, double-spend test, cost=0.0 for mocked calls)
- `python scripts/run_game.py --config mistral-mono --games 1` completes; `grep '"event": "game_end"' data/raw/*/game.jsonl` shows `total_cost_usd ≤ 0.02`
- `grep '"event": "round_end"' data/raw/*/game.jsonl | wc -l` returns exactly 150 (25 rounds × 6 agents)
- `grep '"accepted": true' data/raw/*/game.jsonl | head -1` returns ≥1 result confirming trade path exercised
- `grep '"vp"' data/raw/*/game.jsonl | head -1` confirms field name is `vp` not `victory_points`

## Observability / Diagnostics

- Runtime signals: JSONL `game_start`, `round_start`, `round_end`, `game_end` events form a complete audit trail; `total_cost_usd` in `game_end` gives per-game cost signal
- Inspection surfaces: `jq '.event' data/raw/*/game.jsonl | sort | uniq -c` shows event distribution; `data/raw/{game_id}/checkpoint_r{N:02d}.json` shows last persisted state
- Failure visibility: GM parse failures logged as `gm_parse_failure` events with `round`, `attempt`, `raw_response` (truncated to 500 chars); game crash leaves last checkpoint readable for resume diagnosis
- Redaction constraints: no secrets in JSONL; API keys never logged

## Integration Closure

- Upstream surfaces consumed: `scripts/test_connectivity.py` (copy `strip_md()`, per-provider kwargs verbatim); `src/analysis/h1_kruskal_wallis.py` column contract `[game_id, model_family, round, agent_id, vp]`; `src/analysis/h2_logistic_mixed_effects.py` column contract `[game_id, round, proposer_model, responder_model, pairing, give_resource, want_resource, accepted]`
- New wiring introduced in this slice: `scripts/run_game.py` is the CLI entrypoint; `src/simulation/__init__.py` exports `GameConfig`, `GameRunner`; `tests/test_smoke.py` is the contract test
- What remains before the milestone is truly usable end-to-end: S03 (prompt templates + tolerant parser), S04 (30 calibration games), S05 (OSF registration)

## Tasks

- [x] **T01: Install deps, write config.py and logger.py** `est:45m`
  - Why: All 6 modules depend on `GameConfig` and `GameLogger`. The JSONL schema is the S02→S03 boundary contract — locking it before any other module touches field names prevents mismatches. Installing deps first unblocks `pytest` for T02–T04.
  - Files: `src/simulation/config.py`, `src/simulation/logger.py`, `src/simulation/__init__.py`, `requirements-lock.txt`
  - Do: Install `pytest polars scipy statsmodels scikit-learn networkx seaborn`. Skip `sentence-transformers` (torch wheel uncertain on Python 3.14 — flag in a comment). Freeze to `requirements-lock.txt`. Write `GameConfig` as a Pydantic `BaseModel` with fields: `config_name`, `num_agents`, `num_rounds`, `resources`, `buildings`, `hunger_rate`, `gm_model`, `agent_models` (list mapping agent_id → provider config). Add named-config factory `GameConfig.from_name(name: str)` returning `mistral-mono`, `phase0`, `pairwise-{A}-{B}` instances. Write `GameLogger` with `log(event: str, **fields)` that writes a single JSON line to `data/raw/{game_id}/game.jsonl`; `round_end` events must emit **one line per agent** with flat fields `game_id, model_family, round, agent_id, vp` (not a nested dict). Verify field name is literally `"vp"` not `"victory_points"`.
  - Verify: `python -c "from src.simulation.config import GameConfig; c = GameConfig.from_name('mistral-mono'); assert c.num_rounds == 25"` passes. `python -c "import pytest, polars, scipy"` exits 0.
  - Done when: `pytest` and `polars` importable; `GameConfig.from_name('mistral-mono')` returns a valid config; `GameLogger` writes a `round_end` line readable as JSON with `vp` field present.

- [x] **T02: Write llm_router.py with per-provider routing and mock guards** `est:45m`
  - Why: `agent.py` and `gm.py` both depend on a single routing surface. Getting the per-provider kwargs exactly right here (copied from `test_connectivity.py`) avoids debugging provider-specific failures in later tasks. The R1 reflection override and the `mock_response` cost guard are both high-risk correctness items.
  - Files: `src/simulation/llm_router.py`
  - Do: Set `litellm.drop_params = True` at module level (not per-call). Copy `strip_md()` verbatim from `test_connectivity.py`. Implement `call_llm(agent_id, messages, is_reflection=False, mock_response=None)` that: (1) looks up provider config from `GameConfig` agent_models map, (2) applies per-provider kwargs — Groq/DeepSeek/Mistral get `response_format={"type":"json_object"}`; Gemini gets `thinking={"type":"disabled","budget_tokens":0}` and `max_tokens=200` minimum; (3) if `is_reflection=True` and agent is DeepSeek, switch model to `openrouter/deepseek/deepseek-r1` and set `max_tokens=800`, no json mode; (4) accumulate cost with `(r._hidden_params.get("response_cost") or 0.0)` — **not** `or 0`; (5) include `time.sleep(0.5)` between calls (same pattern as `test_connectivity.py`). Write a `MockLLM` context manager that patches `litellm.completion` with a fixed response for testing. Test mock cost guard: confirm `total_cost` stays `0.0` (not `None`) after a mock call.
  - Verify: `python -c "from src.simulation.llm_router import call_llm; print('ok')"` exits 0. Manual mock test: create a temp script that calls `call_llm` with `mock_response='{"action":"build"}'` and asserts cost accumulates as `0.0`.
  - Done when: `llm_router.py` importable; mock cost guard verified; DeepSeek reflection model override confirmed in code review.

- [x] **T03: Write agent.py and gm.py with double-spend-safe resolution** `est:1h`
  - Why: GM double-spend prevention is the highest-risk correctness item in the entire slice. Testing it in isolation here (before `game.py` adds loop complexity) means a single mock scenario directly exercises the inventory copy logic. Agent's reflection timing (`after round_end`) must be locked before `game.py` wires the loop order.
  - Files: `src/simulation/agent.py`, `src/simulation/gm.py`
  - Do: `Agent` holds `agent_id`, `model_family`, `inventory: dict[str, int]`, `vp: int`, `memory: list[str]`. Implement `act(round_num, game_state) -> dict` (calls `call_llm`, parses JSON action), `respond_to_trade(proposal, game_state) -> dict`, `reflect(round_num, game_state)` (calls `call_llm(is_reflection=True)`, appends summary to `memory`). Reflection fires only on rounds 5/10/15/20/25 and must be called *after* `round_end` is logged — add a docstring comment noting this constraint explicitly so `game.py` cannot ignore it. `GM` implements `resolve_trades(proposals: list, inventories: dict) -> list[Resolution]` using **sequential validation on a working copy**: iterate proposals in order, validate against `working_inv` (not the round-start snapshot), update `working_inv` on each accepted trade. On JSON parse failure after 2 retries, log `gm_parse_failure` event and return all trades as invalid (safe fallback). Emit `gm_resolution` events with all required H2 fields: `round, trade_idx, valid, reason, proposer_model, responder_model, pairing, give_resource, want_resource, accepted`.
  - Verify: Write an inline `if __name__ == "__main__"` double-spend test in `gm.py`: agent A proposes trade (give 2 wood to B) AND (give 2 wood to C), A has exactly 2 wood. Assert first trade accepted, second rejected. Run with `python src/simulation/gm.py`.
  - Done when: Inline double-spend test passes; `agent.py` and `gm.py` importable; reflection timing constraint documented in code.

- [x] **T04: Write game.py, run_game.py, test_smoke.py and run acceptance test** `est:1.5h`
  - Why: Final integration. Wires all 5 prior modules into a running game. `test_smoke.py` locks the schema contract with assertions. The real Mistral smoke run retires the "game mechanics correctness" risk from the roadmap.
  - Files: `src/simulation/game.py`, `scripts/run_game.py`, `tests/test_smoke.py`, `src/simulation/__init__.py`
  - Do: `GameRunner.run_game(config)` orchestrates the 25-round loop: (1) `game_start` event; (2) for each round: `round_start` → collect agent actions → collect trade proposals → collect responses → GM resolution → execute builds → grain consumption → **JSONL flush+fsync** → write `round_end` (one line per agent, flat fields) → write `checkpoint_r{N:02d}.json` (this order — JSONL before checkpoint); (3) reflection for agents on rounds 5/10/15/20/25 *after* `round_end` logged; (4) `game_end` event with `total_cost_usd`. `scripts/run_game.py`: argparse `--config` and `--games`; `uuid4().hex[:8]` game IDs; `Path(f"data/raw/{game_id}").mkdir(parents=True, exist_ok=True)` before first write; `$80` budget cap via `litellm.BudgetManager` initialized once at startup. `tests/test_smoke.py`: 3-round mock game using `mock_response` fixture; assert `round_end` events have `game_id, model_family, round, agent_id, vp` (all present, correct types); assert `gm_resolution` event has `accepted` field; assert `checkpoint_r01.json` exists after round 1; assert `total_cost == 0.0` after 3-round mock (not `None`); assert double-spend scenario rejects second trade. Do NOT import `src.analysis.*` in the test file. Run `pytest tests/test_smoke.py -v`. Then run `python scripts/run_game.py --config mistral-mono --games 1` and verify output JSONL.
  - Verify: `pytest tests/test_smoke.py` all green. `grep '"event": "game_end"' data/raw/*/game.jsonl` shows `total_cost_usd` present and ≤0.02. `grep '"event": "round_end"' data/raw/*/game.jsonl | wc -l` returns 150. `grep '"accepted": true' data/raw/*/game.jsonl | head -1` returns ≥1 result.
  - Done when: `pytest tests/test_smoke.py` passes; real 25-round game completes; JSONL has 150 `round_end` lines; ≥1 accepted trade; `total_cost_usd ≤ 0.02`; `vp` field name confirmed correct.

## Files Likely Touched

- `src/simulation/config.py`
- `src/simulation/logger.py`
- `src/simulation/llm_router.py`
- `src/simulation/agent.py`
- `src/simulation/gm.py`
- `src/simulation/game.py`
- `src/simulation/__init__.py`
- `scripts/run_game.py`
- `tests/test_smoke.py`
- `requirements-lock.txt`
