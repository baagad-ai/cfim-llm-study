---
estimated_steps: 6
estimated_files: 5
---

# T02: Extract and compress prompt builders into src/prompts/ modules

**Slice:** S03 — Prompt Templates + Tolerant Parser
**Milestone:** M001

## Description

Create the 5 prompt modules in `src/prompts/`. Each module is a pure function layer: takes typed arguments (agent state, game state dicts), returns `list[dict]` (chat messages). No LLM calls inside prompt modules.

The critical discipline: extract verbatim first (confirm the module is importable), then compress. Compressing while extracting doubles the failure surface — if something breaks, you can't tell whether the extraction or the compression caused it.

The most behaviorally important work is `trade_response.py`: the current prompt gives agents no strategic reason to accept (D037 — 0 accepted trades in Mistral-mono run). The new system prompt must contain explicit VP-unlocking framing.

Token targets (20% tolerance):
- `act`: ≤108 tok (estimated as `sum(len(m['content']) for m in msgs) // 4`)
- `respond_to_trade`: ≤72 tok
- `reflect`: ≤180 tok (already close at ~215; compress toward 150)
- `gm_resolution`: ≤144 tok (currently under-target; leave as-is or expand slightly)

## Steps

1. **`src/prompts/building_decision.py`** — helper only, no LLM call:
   - `format_building_options(buildings: dict) -> str` — renders building list in compact format: `Market(W2 S2→3vp) Granary(G3 W1→3vp) Tower(S2 C2→3vp)`. Use resource initials (same as `format_inventory`). This gets injected into the `agent_action` system message.

2. **`src/prompts/agent_action.py`**:
   - `build_act_messages(agent_id, model_family, round_num, inventory, vp, buildings_built, all_agents_vp, memory, buildings_config) -> list[dict]`
   - System message (static, cache-able): game overview + all rules + building options (use `format_building_options`) + JSON schema for action response. Must NOT contain agent_id, round, or inventory. Identical for every agent in every round within a game. Aim for ~60-80 tok.
   - User message (dynamic): `Round {N}. You: {agent_id}. Inventory: {format_inventory(inventory)}. VP: {vp}. Built: {buildings_built}. Scores: {compact VP leaderboard e.g. "a0:6 a1:3 a2:3"}. {last 3 memory lines if any}. Choose an action.` Aim for ~20-30 tok.
   - Total target: ≤108 tok.

3. **`src/prompts/trade_response.py`**:
   - `build_respond_messages(agent_id, inventory, vp, proposal, buildings_config) -> list[dict]`
   - System message: strategic framing (see must-haves below) + JSON schema. Static, never varies.
   - User message: `You: {agent_id}. Inventory: {format_inventory(inventory)}. VP: {vp}. Proposal: {proposer} offers {give} for {want}.` No full game_state dump.
   - Total target: ≤72 tok.

4. **`src/prompts/reflection.py`**:
   - `build_reflect_messages(agent_id, round_num, inventory, vp, memory) -> list[dict]`
   - System message: reflection instructions (static). User message: round + inventory + VP + last 3 memory entries.
   - Compress toward 150 tok (±30 tok tolerance). Do NOT include full game_state dict.

5. **`src/prompts/gm_resolution.py`**:
   - `build_gm_messages(round_num, proposals) -> list[dict]` — extracts `_build_gm_prompt` from `gm.py` verbatim, wraps in messages list
   - `build_simple_gm_messages(proposals) -> list[dict]` — extracts `_build_simple_gm_prompt` verbatim
   - These functions return full messages list (not just the prompt string), matching the call pattern in gm.py

6. Verify all 5 modules importable and system messages are purely static:
   ```bash
   python -c "
   from src.prompts.agent_action import build_act_messages
   from src.prompts.trade_response import build_respond_messages
   from src.prompts.gm_resolution import build_gm_messages, build_simple_gm_messages
   from src.prompts.reflection import build_reflect_messages
   from src.prompts.building_decision import format_building_options

   # agent_action system message must not contain 'round' or 'inventory' as dynamic values
   inv = {'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}
   buildings = {'Market':{'cost':{'wood':2,'stone':2},'vp':3},'Granary':{'cost':{'grain':3,'wood':1},'vp':3},'Tower':{'cost':{'stone':2,'clay':2},'vp':3}}
   msgs = build_act_messages('a0', 'mistral', 5, inv, 6, [], {'a0':6,'a1':3}, [], buildings)
   sys_msg = msgs[0]['content']
   assert 'Round' not in sys_msg, 'round in system message breaks caching'
   assert 'a0' not in sys_msg, 'agent_id in system message breaks caching'
   tok_est = sum(len(m['content']) for m in msgs) // 4
   assert tok_est <= 108, f'act token estimate {tok_est} > 108'

   # respond_to_trade system message must contain VP-unlock framing
   proposal = {'proposer':'a1','give':{'wood':1},'want':{'grain':1}}
   msgs2 = build_respond_messages('a0', inv, 6, proposal, buildings)
   sys2 = msgs2[0]['content']
   assert 'building' in sys2.lower() or 'unlock' in sys2.lower() or 'afford' in sys2.lower(), 'VP framing missing'
   tok2 = sum(len(m['content']) for m in msgs2) // 4
   assert tok2 <= 72, f'respond token estimate {tok2} > 72'
   print('T02 ok')
   "
   ```

## Must-Haves

- [ ] `trade_response.py` system message contains at least 2 of: "unlock", "afford", "building", "counter" — strategic VP framing addressing D037
- [ ] `agent_action.py` system message contains no agent-specific or round-specific data (no `agent_id`, no `Round N`, no inventory values)
- [ ] `building_decision.py` `format_building_options` used in agent_action system message (not user message)
- [ ] `reflect` messages do NOT dump full `game_state` dict into user message
- [ ] `gm_resolution.py` returns `list[dict]` (messages), not the raw prompt string
- [ ] Token estimate for `act` ≤108, `respond_to_trade` ≤72 (chars//4 approximation)
- [ ] All 5 modules importable with no circular import errors

## Verification

```bash
cd /Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family
source .venv/bin/activate
python -c "from src.prompts.agent_action import build_act_messages; from src.prompts.trade_response import build_respond_messages; from src.prompts.gm_resolution import build_gm_messages; from src.prompts.reflection import build_reflect_messages; from src.prompts.building_decision import format_building_options; print('all imports ok')"
```

## Inputs

- `src/simulation/agent.py` — `_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages` (source to extract from)
- `src/simulation/gm.py` — `_build_gm_prompt`, `_build_simple_gm_prompt` (source to extract from)
- `src/prompts/json_utils.py` — `format_inventory` used by agent_action and trade_response user messages
- S03-RESEARCH.md §"respond_to_trade fix" — VP-unlocking framing language
- S03-RESEARCH.md §"Token budget strategy" — what goes in system vs user
- D037 — behavioral root cause requiring strategic framing in respond_to_trade

## Expected Output

- `src/prompts/agent_action.py` — compressed act messages builder; static system, compact user
- `src/prompts/trade_response.py` — respond messages builder; VP-unlock framing in system
- `src/prompts/reflection.py` — reflect messages builder; no full game_state dump
- `src/prompts/gm_resolution.py` — GM messages builders (normal + simplified retry)
- `src/prompts/building_decision.py` — `format_building_options` helper
