# S03: Prompt Templates + Tolerant Parser

**Goal:** Extract and compress prompt builders into `src/prompts/`, implement a tolerant JSON parser, fix the phase0 config, and redesign `respond_to_trade` so agents have a strategic reason to accept.
**Demo:** `pytest tests/test_prompts.py` passes all edge-case parse tests; `pytest tests/test_smoke.py` still passes 5/5 after the agent/gm wiring swap; `GameConfig.from_name('phase0')` returns a real 4-family mix; token counts for `act` and `respond_to_trade` are within 20% of blueprint targets.

## Must-Haves

- `src/prompts/json_utils.py` with `parse_agent_response(raw, schema)` handling all 5 input cases (valid, fenced, surrounded, truncated, think-prefixed); returns `None` on unrecoverable failure
- `src/prompts/{agent_action,trade_response,gm_resolution,building_decision,reflection}.py` — all 5 prompt modules; system messages are static (cache-able); user messages carry only dynamic per-round data
- `agent.py` and `gm.py` wired to import from `src/prompts/` — prompt text lives in `src/prompts/`, not inline
- `GameConfig.from_name('phase0')` returns 2 Llama + 2 DeepSeek + 1 Gemini + 1 Mistral (6 agents); `llama-mono`, `deepseek-mono`, `gemini-mono` added to `from_name()`
- `respond_to_trade` system prompt contains explicit VP-unlocking framing (strategic incentive to accept)
- `act` token count ≤ 108 tok (20% over 90-tok target); `respond_to_trade` ≤ 72 tok (20% over 60-tok target)
- `pytest tests/test_smoke.py -v` passes 5/5 after wiring
- `pytest tests/test_prompts.py -v` passes all tests covering all 5 parse cases + token budget checks + phase0 config shape

## Proof Level

- This slice proves: contract (prompt module interface + parser correctness) + integration (agent/gm wiring with smoke gate)
- Real runtime required: no (all tests use mock LLM responses)
- Human/UAT required: no

## Verification

```
pytest tests/test_smoke.py -v             # 5/5 must pass — wiring integration gate
pytest tests/test_prompts.py -v           # all pass — parser edge cases + token budgets
python -c "from src.simulation.config import GameConfig; c = GameConfig.from_name('phase0'); fams = {e['model_family'] for e in c.agent_models}; assert fams == {'llama','deepseek','gemini','mistral'}, fams; print('phase0 ok')"
grep -c '"accepted": true' data/raw/*/game.jsonl  # baseline (expected 0 from S02 run — new prompt targets >0 in S04)
```

## Observability / Diagnostics

- Runtime signals: `parse_agent_response` logs at WARNING level on each fallback strategy used (fence strip, JSON extraction, truncation detected); returns `None` so callers' fallback paths are exercised
- Inspection surfaces: `python -c "from src.prompts.json_utils import parse_agent_response; print(parse_agent_response('<think>r</think>\n{\"action_type\":\"hoard\"}', {}))"` — quick single-case smoke
- Failure visibility: parse failure returns `None` (not silent fallback dict); callers log "hoarding due to parse failure" so grep on WARNING reveals parse degradation rate
- Redaction constraints: none — no secrets in prompt text

## Integration Closure

- Upstream surfaces consumed: `strip_md()` from `src/simulation/llm_router.py` (imported by `json_utils.py`); `PROVIDER_KWARGS` from same (consumed by `get_completion_kwargs()`); `GameConfig` field names from `src/simulation/config.py` (prompt variables must use locked names)
- New wiring introduced: `agent.py` replaces `_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages` with imports from `src/prompts/`; `gm.py` replaces `_build_gm_prompt`, `_build_simple_gm_prompt` with imports from `src/prompts/gm_resolution.py`
- What remains before milestone is truly usable end-to-end: S04 (Phase 0 calibration games with these prompts)

## Tasks

- [x] **T01: Implement json_utils.py with tolerant parser and formatting helpers** `est:45m`
  - Why: All prompt modules depend on `parse_agent_response()` and `format_inventory()`. Building this first isolates the parser correctness problem from prompt authoring and makes the failure mode explicit (None return) before any wiring happens.
  - Files: `src/prompts/json_utils.py`, `src/prompts/__init__.py`
  - Do: Implement `parse_agent_response(raw, schema) -> dict | None` with 4-strategy fallback chain: (1) direct `json.loads` after `strip_md()`, (2) strip `<think>...</think>` then parse, (3) bracket-counter JSON extraction then parse, (4) return `None`. Catch only `json.JSONDecodeError`, `ValueError`, `TypeError`. Log at WARNING on each fallback used. Implement `format_inventory(inv: dict) -> str` → compact `W2 S3 G4 C1 F2` format. Implement `get_completion_kwargs(model_family: str) -> dict` → looks up `PROVIDER_KWARGS` from `llm_router.py`; do not copy the dict. Import `strip_md` from `llm_router.py` (do not copy it).
  - Verify: `python -c "from src.prompts.json_utils import parse_agent_response, format_inventory; assert parse_agent_response('{\"action_type\": \"hoard\"}', {}) == {'action_type': 'hoard'}; assert parse_agent_response('{\"action_type\": \"bu', {}) is None; assert format_inventory({'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}) == 'W2 S3 G4 C1 F0'; print('ok')"`
  - Done when: All 3 assert-based spot checks pass; module importable with no errors

- [x] **T02: Extract and compress prompt builders into src/prompts/ modules** `est:1h`
  - Why: The prompt text needs to live in `src/prompts/` so S04's format ablation can test templates in isolation without running full games. Extraction must happen before compression to keep failure surface clean — if smoke fails after extraction alone, the bug is in the extraction, not the compression.
  - Files: `src/prompts/agent_action.py`, `src/prompts/trade_response.py`, `src/prompts/reflection.py`, `src/prompts/gm_resolution.py`, `src/prompts/building_decision.py`
  - Do: For each module, write a pure function `build_<type>_messages(...)` returning `list[dict]`. Extract verbatim from agent.py/gm.py first (exact same text), then compress in the same commit. `agent_action.py`: system message contains all game rules + building costs + JSON schema (static, cache-able); user message is round + inventory (compact `format_inventory()`) + VP + recent proposals — target ≤108 tok total. `trade_response.py`: system message contains strategic framing ("Trading unlocks buildings you can't afford alone", "If they have what you need, a fair trade gets you closer to building", "Counter-proposing is better than flat declining") + JSON schema; user message is just inventory + proposal — target ≤72 tok. `reflection.py`: system message has reflection instructions; user message has round + VP + compact inventory + last 3 memories — within 20% tolerance already (~215 tok, target 120–180; compress toward lower end). `gm_resolution.py`: `build_gm_messages(round_num, proposals)` and `build_simple_gm_messages(proposals)` — extracts `_build_gm_prompt` and `_build_simple_gm_prompt` from gm.py with no behavior change. `building_decision.py`: `format_building_options(buildings: dict) -> str` helper — formats buildings list for injection into agent_action system prompt; no separate LLM call. Never put agent_id, round, or inventory in the system message.
  - Verify: `python -c "from src.prompts.agent_action import build_act_messages; from src.prompts.trade_response import build_respond_messages; from src.prompts.gm_resolution import build_gm_messages; print('imports ok')"` — all 5 modules importable
  - Done when: All 5 modules importable; `build_act_messages` system message contains no round/agent/inventory data (verified by inspection); token estimate for act ≤108 and respond_to_trade ≤72

- [x] **T03: Wire agent.py + gm.py to src/prompts/ and fix GameConfig** `est:45m`
  - Why: The integration step is the slice's correctness gate. Replacing inline builders with imports must not change observable behavior — test_smoke.py 5/5 is the proof. GameConfig changes (phase0, mono configs) are in this task because they're low-risk additions that S04 needs.
  - Files: `src/simulation/agent.py`, `src/simulation/gm.py`, `src/simulation/config.py`
  - Do: In `agent.py`: replace `_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages` with `from src.prompts.agent_action import build_act_messages`, `from src.prompts.trade_response import build_respond_messages`, `from src.prompts.reflection import build_reflect_messages`; update the three call sites in `act()`, `respond_to_trade()`, `reflect()`. Update `act()` and `respond_to_trade()` to call `parse_agent_response()` from `json_utils` instead of bare `json.loads` (keep the same `None` → fallback dict pattern; fallback values stay in the caller, not in the parser). In `gm.py`: replace `_build_gm_prompt` and `_build_simple_gm_prompt` with imports from `src.prompts.gm_resolution`; remove the local function definitions. In `config.py`: add `_mixed_4family()` builder (a0-a1: llama, a2-a3: deepseek, a4: gemini, a5: mistral); update `from_name('phase0')` to call it. Add `llama-mono`, `deepseek-mono`, `gemini-mono` to `from_name()` using the `_mistral_mono` pattern. Update `from_name()` error message to list all valid names.
  - Verify: `pytest tests/test_smoke.py -v` → 5 passed; `python -c "from src.simulation.config import GameConfig; c = GameConfig.from_name('phase0'); fams = {e['model_family'] for e in c.agent_models}; assert fams == {'llama','deepseek','gemini','mistral'}; print('ok')"`
  - Done when: `pytest tests/test_smoke.py -v` shows 5 passed with no warnings about import errors

- [x] **T04: Write tests/test_prompts.py covering all parser cases and token budgets** `est:45m`
  - Why: The S03 slice success criterion is "pytest tests/test_prompts.py passes all edge-case parse tests." This is the final verification that the parser handles all 5 input cases and that the compressed prompts are within budget.
  - Files: `tests/test_prompts.py`
  - Do: Write pytest classes: `TestParseAgentResponse` — 5 tests, one per case: valid JSON (returns dict), fenced JSON (returns dict), JSON with surrounding text (returns dict), truncated JSON (returns None), DeepSeek think-block prefix (returns dict). `TestFormatInventory` — compact format output matches expected `W2 S3` etc. `TestTokenBudgets` — build act messages with a realistic agent state; estimate `sum(len(m['content']) for m in msgs) // 4 ≤ 108`; same for respond_to_trade ≤ 72. `TestPhase0Config` — `GameConfig.from_name('phase0')` has 6 agents; all 4 families present; exactly 2 llama, 2 deepseek, 1 gemini, 1 mistral. `TestMonoConfigs` — `from_name('llama-mono')`, `from_name('deepseek-mono')`, `from_name('gemini-mono')` all return configs with 6 agents of the expected family. `TestGetCompletionKwargs` — `get_completion_kwargs('gemini')` does not contain `response_format`; `get_completion_kwargs('mistral')` contains `response_format`. No real API calls; no polars imports.
  - Verify: `pytest tests/test_prompts.py -v` → all tests pass
  - Done when: All tests pass with zero failures; no skips; no real API calls made

## Files Likely Touched

- `src/prompts/__init__.py`
- `src/prompts/json_utils.py`
- `src/prompts/agent_action.py`
- `src/prompts/trade_response.py`
- `src/prompts/gm_resolution.py`
- `src/prompts/building_decision.py`
- `src/prompts/reflection.py`
- `src/simulation/agent.py`
- `src/simulation/gm.py`
- `src/simulation/config.py`
- `tests/test_prompts.py`
