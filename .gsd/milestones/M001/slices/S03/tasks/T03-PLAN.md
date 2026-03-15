---
estimated_steps: 5
estimated_files: 3
---

# T03: Wire agent.py + gm.py to src/prompts/ and fix GameConfig

**Slice:** S03 — Prompt Templates + Tolerant Parser
**Milestone:** M001

## Description

Replace the inline prompt builder functions in `agent.py` and `gm.py` with imports from `src/prompts/`. Update the JSON parsing in `agent.py` to use `parse_agent_response()` from `json_utils`. Add the phase0 4-family config and missing mono configs to `config.py`.

This is the integration task — the smoke gate (5/5) is the acceptance criterion, not the code changes themselves. If smoke fails, stop and fix wiring before any other work.

Key constraint: the observable behavior of `act()`, `respond_to_trade()`, and `reflect()` must not change. The return type, fallback behavior, and error handling paths stay identical — only the prompt text source changes.

## Steps

1. **`src/simulation/agent.py`** — swap prompt builders and update parser:
   - Add imports at top: `from src.prompts.agent_action import build_act_messages`, `from src.prompts.trade_response import build_respond_messages`, `from src.prompts.reflection import build_reflect_messages`, `from src.prompts.json_utils import parse_agent_response`
   - In `act()`: replace `messages = _build_act_messages(self, round_num, game_state)` with the new call signature. The new `build_act_messages` takes explicit args (not the whole agent object and raw game_state dict) — pass: `agent_id=self.agent_id, model_family=self.model_family, round_num=round_num, inventory=self.inventory, vp=self.vp, buildings_built=self.buildings_built, all_agents_vp=game_state.get('vp', {}), memory=self.memory[-3:], buildings_config=game_state.get('buildings', {})`. Replace `action = json.loads(content)` with `action = parse_agent_response(content, {})`. Keep the `if action is None: return {"action_type": "hoard"}` fallback in `act()` (not inside the parser).
   - In `respond_to_trade()`: replace messages call; replace `json.loads(content)` with `parse_agent_response(content, {})`; keep `if response is None: return {"accepted": False, "counter": None}` fallback in the caller.
   - In `reflect()`: replace messages call with `build_reflect_messages(agent_id=self.agent_id, round_num=round_num, inventory=self.inventory, vp=self.vp, memory=self.memory)`.
   - Remove the now-unused `_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages` functions.

2. **`src/simulation/gm.py`** — swap GM prompt builders:
   - Add imports: `from src.prompts.gm_resolution import build_gm_messages, build_simple_gm_messages`
   - In `_get_gm_verdicts()`: replace `prompt = _build_gm_prompt(...)` + messages list construction with `messages = build_gm_messages(round_num, proposals)`. Replace simplified retry with `messages = build_simple_gm_messages(proposals)`.
   - Remove the now-unused `_build_gm_prompt` and `_build_simple_gm_prompt` functions.

3. **`src/simulation/config.py`** — add phase0 and mono configs:
   - Add `_mixed_4family()` classmethod: a0→llama, a1→llama, a2→deepseek, a3→deepseek, a4→gemini, a5→mistral. Returns `cls(config_name="phase0", ...)`.
   - Update `from_name('phase0')` to call `cls._mixed_4family()` (remove the placeholder mistral-mono fallback).
   - Add `"llama-mono"`: calls `cls._mono("llama")` or equivalent pattern.
   - Add `"deepseek-mono"`: same pattern.
   - Add `"gemini-mono"`: same pattern.
   - Extract a `_mono(family)` helper to avoid repeating the list comprehension 4 times.
   - Update the `raise ValueError` error message to list all valid names including new ones.

4. Run smoke test immediately. If any test fails, stop and diagnose before proceeding:
   ```bash
   pytest tests/test_smoke.py -v
   ```
   If fails: check import errors first (`python -c "from src.simulation.agent import Agent"`), then check the call signature mismatch between the new prompt module and the agent call site.

5. Verify phase0 config shape:
   ```bash
   python -c "
   from src.simulation.config import GameConfig
   c = GameConfig.from_name('phase0')
   fams = [e['model_family'] for e in c.agent_models]
   assert len(c.agent_models) == 6
   assert fams.count('llama') == 2
   assert fams.count('deepseek') == 2
   assert fams.count('gemini') == 1
   assert fams.count('mistral') == 1
   for name in ('llama-mono', 'deepseek-mono', 'gemini-mono', 'mistral-mono'):
       cfg = GameConfig.from_name(name)
       fam = name.split('-')[0]
       assert all(e['model_family'] == fam for e in cfg.agent_models), name
   print('config ok')
   "
   ```

## Must-Haves

- [ ] `pytest tests/test_smoke.py -v` → 5 passed (hard gate — do not advance to T04 until this passes)
- [ ] `parse_agent_response` called in `act()` and `respond_to_trade()`; `None` → fallback dict in caller, not in parser
- [ ] `_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages` removed from `agent.py`
- [ ] `_build_gm_prompt`, `_build_simple_gm_prompt` removed from `gm.py`
- [ ] `GameConfig.from_name('phase0')` returns 2 llama + 2 deepseek + 1 gemini + 1 mistral
- [ ] `llama-mono`, `deepseek-mono`, `gemini-mono` registered in `from_name()`

## Verification

```bash
cd /Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family
source .venv/bin/activate
pytest tests/test_smoke.py -v
python -c "from src.simulation.config import GameConfig; c = GameConfig.from_name('phase0'); fams = {e['model_family'] for e in c.agent_models}; assert fams == {'llama','deepseek','gemini','mistral'}; print('phase0 ok')"
```

## Observability Impact

- Signals added/changed: `parse_agent_response` logs at WARNING on each fallback strategy (fence strip, think strip, bracket extraction). These appear in stderr during game runs — grep for `"WARNING"` to see parse degradation rate.
- How a future agent inspects this: `grep -i "fallback\|parse.*fail" /tmp/game_run.log` or enable logging in the runner
- Failure state exposed: `act()` and `respond_to_trade()` now expose `None` parse result before applying fallback — the WARNING log shows which strategy triggered

## Inputs

- `src/prompts/agent_action.py`, `src/prompts/trade_response.py`, `src/prompts/reflection.py` — from T02
- `src/prompts/gm_resolution.py` — from T02
- `src/prompts/json_utils.py` — `parse_agent_response` — from T01
- `src/simulation/agent.py` — current call sites for `_build_*_messages()` and `json.loads(content)`
- `src/simulation/gm.py` — current call sites for `_build_gm_prompt()` and `_build_simple_gm_prompt()`
- `src/simulation/config.py` — current `from_name()` and `_mistral_mono()` pattern to follow

## Expected Output

- `src/simulation/agent.py` — wired to src/prompts/; parse_agent_response used; old builders removed
- `src/simulation/gm.py` — wired to gm_resolution module; old builders removed
- `src/simulation/config.py` — phase0 = 4-family mix; llama/deepseek/gemini mono configs added
