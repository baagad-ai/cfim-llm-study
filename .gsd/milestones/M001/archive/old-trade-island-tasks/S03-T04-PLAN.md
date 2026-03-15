---
estimated_steps: 4
estimated_files: 1
---

# T04: Write tests/test_prompts.py covering all parser cases and token budgets

**Slice:** S03 — Prompt Templates + Tolerant Parser
**Milestone:** M001

## Description

Write the slice verification test file. This is the final gate for S03. All tests use synthetic inputs — no real API calls, no polars imports.

The parser tests are straightforward — each covers one row from the "What parse_agent_response() must handle" table in the research notes. The token budget tests use the chars//4 approximation; the ±20% tolerance absorbs estimation error.

## Steps

1. Create `tests/test_prompts.py` with these test classes:

   **`TestParseAgentResponse`** — 5 test methods:
   - `test_valid_json` — `parse_agent_response('{"action_type": "hoard"}', {})` returns `{'action_type': 'hoard'}`
   - `test_fenced_json` — input is `` ```json\n{"action_type":"build"}\n``` `` (markdown fence); returns parsed dict
   - `test_json_with_surrounding_text` — input is `'Here is my action: {"action_type":"build"} done.'`; returns `{'action_type': 'build'}`
   - `test_truncated_json_returns_none` — input is `'{"action_type": "bu'`; returns `None`
   - `test_deepseek_think_prefix` — input is `'<think>I should hoard this round</think>\n{"action_type":"hoard"}'`; returns `{'action_type': 'hoard'}`

   **`TestFormatInventory`**:
   - `test_compact_format` — `format_inventory({'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0})` == `'W2 S3 G4 C1 F0'`
   - `test_empty_values` — zeroes appear in output (not omitted): `format_inventory({'wood':0,'stone':0,'grain':0,'clay':0,'fiber':0})` == `'W0 S0 G0 C0 F0'`

   **`TestTokenBudgets`**:
   - `test_act_within_budget` — call `build_act_messages` with realistic agent state; `sum(len(m['content']) for m in msgs) // 4 <= 108`
   - `test_respond_within_budget` — call `build_respond_messages` with typical proposal; `sum(...) // 4 <= 72`
   - Use these realistic values: inventory `{'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}`, vp=6, round=8, buildings config from `_STANDARD_BUILDINGS`

   **`TestPhase0Config`**:
   - `test_phase0_has_four_families` — `GameConfig.from_name('phase0')` has all 4 families: `{e['model_family'] for e in c.agent_models} == {'llama','deepseek','gemini','mistral'}`
   - `test_phase0_agent_count` — exactly 6 agents
   - `test_phase0_family_distribution` — exactly 2 llama, 2 deepseek, 1 gemini, 1 mistral

   **`TestMonoConfigs`**:
   - `test_llama_mono` — `GameConfig.from_name('llama-mono')` → 6 agents, all `model_family == 'llama'`
   - `test_deepseek_mono` — same pattern for deepseek
   - `test_gemini_mono` — same pattern for gemini

   **`TestGetCompletionKwargs`**:
   - `test_gemini_no_response_format` — `get_completion_kwargs('gemini')` does not contain `response_format`
   - `test_mistral_has_response_format` — `get_completion_kwargs('mistral')` contains `response_format`
   - `test_returns_copy` — modifying returned dict does not modify PROVIDER_KWARGS

2. Add necessary imports at top: `from src.prompts.json_utils import ...`, `from src.prompts.agent_action import ...`, etc. No `src.analysis.*` imports. No `polars` imports.

3. Run and confirm all pass:
   ```bash
   pytest tests/test_prompts.py -v
   ```

4. Run full suite to confirm no regressions:
   ```bash
   pytest tests/ -v
   ```

## Must-Haves

- [ ] All 5 parse cases covered with explicit assertions
- [ ] `test_truncated_json_returns_none` asserts `result is None` (not just falsy)
- [ ] Token budget tests use `≤` not `==` (tolerance, not exact match)
- [ ] `TestPhase0Config.test_phase0_family_distribution` checks exact counts (2/2/1/1)
- [ ] No `src.analysis.*` imports; no `polars` imports
- [ ] `pytest tests/ -v` → all tests pass (no regressions in test_smoke.py)

## Verification

```bash
cd /Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family
source .venv/bin/activate
pytest tests/test_prompts.py -v
pytest tests/test_smoke.py -v
```

Both must show all tests passing with zero failures.

## Inputs

- `src/prompts/json_utils.py` — parser and helpers under test (T01)
- `src/prompts/agent_action.py`, `src/prompts/trade_response.py` — token budget under test (T02)
- `src/simulation/config.py` — phase0 and mono config shapes under test (T03)
- `tests/test_smoke.py` — pattern for no-polars, mock-LLM test style

## Expected Output

- `tests/test_prompts.py` — all tests pass; covers parser edge cases, token budgets, config shapes, kwarg inspection
