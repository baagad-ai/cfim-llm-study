---
id: T02
parent: S03
milestone: M001
provides:
  - src/prompts/agent_action.py — static system + compact user build_act_messages
  - src/prompts/trade_response.py — VP-unlock framing build_respond_messages (D037 fix)
  - src/prompts/reflection.py — no game_state dump build_reflect_messages
  - src/prompts/gm_resolution.py — build_gm_messages + build_simple_gm_messages returning list[dict]
  - src/prompts/building_decision.py — format_building_options helper
key_files:
  - src/prompts/agent_action.py
  - src/prompts/trade_response.py
  - src/prompts/reflection.py
  - src/prompts/gm_resolution.py
  - src/prompts/building_decision.py
key_decisions:
  - D038 — pure-function prompt layer; explicit args, no Agent object or game_state dict
  - D037 — VP-unlock framing in respond_to_trade: 4/4 keywords present (unlock, afford, building, counter)
patterns_established:
  - Static system message (all rules + schema) + compact user tail (round + inventory via format_inventory + VP); never put agent_id/round/inventory values in system
  - VP-framing in trade_response._SYSTEM addresses D037 — "Trades unlock buildings you can't afford alone; counter-propose instead of flat declining"
  - format_building_options injected into act system message (not user message) — cache-safe
  - gm_resolution wraps verbatim prompt strings in list[dict] messages; retry logic stays in gm.py
observability_surfaces:
  - python -c "from src.prompts.agent_action import build_act_messages; msgs = build_act_messages('a0','mistral',1,{'wood':2},0,[],{'a0':0},[],{}); print(msgs[0]['content'])" — inspect static system
  - python -c "from src.prompts.trade_response import _SYSTEM; print(_SYSTEM)" — inspect VP-framing text
duration: 30m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Extract and compress prompt builders into src/prompts/ modules

**All 5 prompt modules created; act=84 tok, respond_to_trade=66 tok; D037 VP-unlock framing verified; test_smoke.py 5/5.**

## What Happened

Created all 5 prompt modules as pure-function layers with no LLM calls:

1. **`building_decision.py`** — `format_building_options(buildings)` renders compact `Market(W2 S2→3vp)` format; uses shared `_RESOURCE_ORDER`/`_RESOURCE_INITIALS` from `json_utils.py` for ordering consistency.

2. **`agent_action.py`** — `build_act_messages(...)` with fully static system message: game rules + building options via `format_building_options` + JSON schema. Zero agent_id/round/inventory data in system. User message is a 1-line compact tail: `R5. You:a0. Inv:W2 S3 G4 C1 F0. VP:6. Scores:a0:6 a1:3 a2:3. Act?`. Compressed from ~260 tok to **84 tok**.

3. **`trade_response.py`** — `build_respond_messages(...)` with a module-level `_SYSTEM` constant (fully static). The system prompt directly addresses D037 with VP-unlock framing: "Trades unlock buildings you can't afford alone — accept if it gets you closer to a building. Counter-propose instead of flat declining." First draft was 94 tok (over 72 limit); tightened prose to reach **66 tok**. Contains all 4 framing keywords: unlock, afford, building, counter.

4. **`reflection.py`** — `build_reflect_messages(...)`. Static system with 2-sentence reflection instruction. User message: round, agent ID, compact inventory, VP, last 3 memory entries. No `game_state` dict — no `{` in user content.

5. **`gm_resolution.py`** — `build_gm_messages(round_num, proposals)` and `build_simple_gm_messages(proposals)`. Both return `list[dict]` messages wrapping verbatim prompt text extracted from `gm.py`. Two-attempt retry logic stays in `gm.py`; only prompt text lives here.

## Verification

```
# Full task-plan verification suite
python -c "
  from src.prompts.agent_action import build_act_messages
  ...
  assert 'Round' not in sys_msg  # no round in system
  assert 'a0' not in sys_msg     # no agent_id in system
  assert tok_est <= 108          # act: 84 tok ✓
  assert tok2 <= 72              # respond: 66 tok ✓
  assert 'building' in sys2.lower()  # VP framing ✓
  print('T02 ok')
"
→ T02 ok

# Must-have checks
→ VP framing keywords found: ['unlock', 'afford', 'building', 'counter']  # 4/4 ✓
→ format_building_options in system message ✓
→ no game_state dict in reflect user message ✓
→ gm returns list[dict] ✓

# Smoke gate
pytest tests/test_smoke.py -v  → 5 passed ✓
```

## Diagnostics

```bash
# Inspect act system message (should be identical for all agents/rounds)
python -c "from src.prompts.agent_action import build_act_messages; msgs = build_act_messages('a0','mistral',1,{'wood':2,'stone':1,'grain':3,'clay':0,'fiber':0},3,[],{'a0':3},[],{'Market':{'cost':{'wood':2,'stone':2},'vp':3}}); print('SYS:', msgs[0]['content']); print('USR:', msgs[1]['content'])"

# Inspect trade VP-framing
python -c "from src.prompts.trade_response import _SYSTEM; print(_SYSTEM)"

# Token budget spot check
python -c "
from src.prompts.agent_action import build_act_messages
from src.prompts.trade_response import build_respond_messages
inv={'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}
b={'Market':{'cost':{'wood':2,'stone':2},'vp':3}}
msgs=build_act_messages('a0','mistral',5,inv,6,[],{'a0':6,'a1':3},[],b)
print('act_tok=', sum(len(m['content']) for m in msgs)//4)
msgs2=build_respond_messages('a0',inv,6,{'proposer':'a1','give':{'wood':1},'want':{'grain':1}},b)
print('respond_tok=', sum(len(m['content']) for m in msgs2)//4)
"
```

## Deviations

- `trade_response._SYSTEM` required one compression pass: first draft at 94 tok exceeded 72 limit. Tightened prose to 66 tok in same task (within T02 scope, not a plan deviation). VP-framing keywords preserved through compression.

## Known Issues

- `agent.py` and `gm.py` still use their inline `_build_*` functions — wiring to `src/prompts/` is T03's job.
- `tests/test_prompts.py` does not exist yet — T04's job.

## Files Created/Modified

- `src/prompts/building_decision.py` — `format_building_options(buildings)` helper; compact building list renderer
- `src/prompts/agent_action.py` — `build_act_messages(...)` with static system + compact user; 84 tok total
- `src/prompts/trade_response.py` — `build_respond_messages(...)` with VP-unlock `_SYSTEM`; 66 tok total
- `src/prompts/reflection.py` — `build_reflect_messages(...)` with no game_state dump in user message
- `src/prompts/gm_resolution.py` — `build_gm_messages()` + `build_simple_gm_messages()` returning `list[dict]`
