---
id: T03
parent: S03
milestone: M001
provides:
  - src/simulation/agent.py — wired to src/prompts/; parse_agent_response used in act() and respond_to_trade(); old inline builders removed
  - src/simulation/gm.py — wired to gm_resolution module; old _build_gm_prompt/_build_simple_gm_prompt removed
  - src/simulation/config.py — phase0 = 2×llama + 2×deepseek + 1×gemini + 1×mistral; llama-mono, deepseek-mono, gemini-mono added via _mono() helper
  - src/prompts/json_utils.py — circular import fixed via lazy imports (D040)
key_files:
  - src/simulation/agent.py
  - src/simulation/gm.py
  - src/simulation/config.py
  - src/prompts/json_utils.py
key_decisions:
  - D040 — lazy import of strip_md and PROVIDER_KWARGS in json_utils.py to break circular import with src.simulation.__init__
patterns_established:
  - Lazy function-level imports to break circular init chains without restructuring package boundaries
  - _mono(family) helper extracts the list-comprehension pattern shared by all 4 mono configs
  - None-check + fallback dict kept in caller (act/respond_to_trade), not inside parse_agent_response — parser is pure, callers own recovery
observability_surfaces:
  - parse_agent_response logs at WARNING per fallback strategy with 80-char input preview; returns None so callers' fallback paths are exercised and logged
  - "python -c \"from src.prompts.json_utils import parse_agent_response; print(parse_agent_response('<think>r</think>\\n{\\\"action_type\\\":\\\"hoard\\\"}', {}))\"" — quick single-case smoke
  - grep for "parse_agent_response.*strategy" or "parse.*None.*hoarding" in run logs to track parse degradation rate
duration: ~30m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Wire agent.py + gm.py to src/prompts/ and fix GameConfig

**Wired agent.py and gm.py to src/prompts/, replaced json.loads with parse_agent_response, and added real phase0 4-family config plus 3 new mono configs; pytest tests/test_smoke.py 5/5.**

## What Happened

Replaced the inline `_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages` functions in `agent.py` with imports from `src.prompts`. Updated `act()` and `respond_to_trade()` to call `parse_agent_response()` from `json_utils` — `None` return still triggers the fallback dict in the caller, not inside the parser. `reflect()` now calls `build_reflect_messages` with explicit args (no game_state dict passed in).

Replaced `_build_gm_prompt` and `_build_simple_gm_prompt` in `gm.py` with imports from `src.prompts.gm_resolution`. Both local function definitions removed.

In `config.py`: extracted a `_mono(family)` helper, added `llama-mono`, `deepseek-mono`, `gemini-mono` to `from_name()`, and implemented `_mixed_4family()` returning 2×llama + 2×deepseek + 1×gemini + 1×mistral for `phase0`. The old `_mistral_mono(config_name=...)` pattern was replaced by the generic `_mono(family)` helper.

**Circular import fix (D040):** After wiring, `src.prompts.json_utils` had a circular dependency: `json_utils` → `src.simulation.llm_router` triggers `src.simulation.__init__` → `game.py` → `agent.py` → `src.prompts.agent_action` → `building_decision` → back to `json_utils` (partially initialized). Smoke tests still passed (they enter via `src.simulation` first so both packages were loaded before `json_utils` needed `llm_router`), but the T03 observability check `python -c "from src.prompts.json_utils import ..."` failed with `ImportError`. Fixed by making the two `llm_router` imports lazy (inside `parse_agent_response()` and `get_completion_kwargs()` respectively). This is a pre-existing issue introduced in T02 that only surfaced here when entering via `src.prompts` as the entry point.

## Verification

```
pytest tests/test_smoke.py -v                           → 5 passed (hard gate)
python -c "from src.simulation.config import GameConfig
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
print('config ok')"                                     → config ok

python -c "from src.prompts.json_utils import parse_agent_response
print(parse_agent_response('<think>r</think>\n{\"action_type\":\"hoard\"}', {}))"
→ WARNING logged; {'action_type': 'hoard'} returned

import src.prompts                                      → ok (circular import resolved)
```

Slice-level checks at T03 completion:
- `pytest tests/test_smoke.py -v` → 5/5 PASS
- `python -c "... phase0 == {'llama','deepseek','gemini','mistral'} ..."` → PASS
- `pytest tests/test_prompts.py -v` → NOT RUN (file not yet created — T04's responsibility)
- `grep -c '"accepted": true' data/raw/*/game.jsonl` → 0 (no game.jsonl yet — baseline established in S02 run; target >0 in S04)

## Diagnostics

```bash
# Single-case observability smoke
python -c "
import logging; logging.basicConfig(level=logging.WARNING)
from src.prompts.json_utils import parse_agent_response
print(parse_agent_response('<think>r</think>\n{\"action_type\":\"hoard\"}', {}))
"

# Check agent imports cleanly
python -c "from src.simulation.agent import Agent; print('ok')"

# Check prompts package imports cleanly
python -c "import src.prompts; print('ok')"

# Trace parse degradation in a run log
grep "parse_agent_response.*strategy\|hoarding due to parse" /tmp/game_run.log
```

## Deviations

**Circular import fix added to json_utils.py (T02 residual):** The task plan did not mention a circular import issue, but one existed in the T02 deliverable (`json_utils.py` importing `llm_router` at module level). It only became visible when running the T03 observability check which enters via `src.prompts` as the import root. Fixed in T03 by making the two `llm_router` imports lazy. Documented as D040.

## Known Issues

None.

## Files Created/Modified

- `src/simulation/agent.py` — replaced 3 inline `_build_*_messages` functions with imports from `src.prompts`; replaced `json.loads(content)` with `parse_agent_response(content, {})` in `act()` and `respond_to_trade()`; removed old builders
- `src/simulation/gm.py` — added import of `build_gm_messages, build_simple_gm_messages`; replaced inline messages construction in `_get_gm_verdicts()` with module calls; removed `_build_gm_prompt` and `_build_simple_gm_prompt`
- `src/simulation/config.py` — added `_mono(family)`, `_mixed_4family()`; added `llama-mono`, `deepseek-mono`, `gemini-mono` to `from_name()`; updated error message to list all valid names
- `src/prompts/json_utils.py` — moved `strip_md` and `PROVIDER_KWARGS` imports to be lazy (inside functions) to break circular init chain (D040)
