# T04: Prompt Rebuild — RULES_BLOCK + All Prompt Modules

**Slice:** S05 — Simulation Engine v2
**Status:** ⬜ Not started
**Est:** 2h

## Goal

Give agents complete rules knowledge via a shared RULES_BLOCK constant. Rebuild all four prompt modules (agent_action, trade_response, reflection, broadcast) to use it. Add gift action schema. Make trade_response system fully static (cache-friendly).

## Files
- Create: `src/prompts/rules.py`
- Modify: `src/prompts/agent_action.py`
- Modify: `src/prompts/trade_response.py`
- Modify: `src/prompts/reflection.py`
- Create: `tests/test_prompts_v2.py`

## rules.py — RULES_BLOCK

```python
RULES_BLOCK = """TRADE ISLAND v2 RULES
======================
GOAL: First to 10 VP wins. Game ends at round 25 if no winner.

RESOURCES (5 types): wood, stone, grain, clay, fiber
  Grain: consumed 1/round. grain=0 at round end → -1 VP.
  Grain+fiber: spoil if held >3 units (excess decays each round). Trade before they rot.
  Other resources (wood, stone, clay): durable, no decay.

PRODUCTION:
  You passively gain +1 of your specialty resource each round automatically.
  HOARD action: gain +2 specialty instead (total +3 that round, vs +1 passive).
  Granary building: +2 grain/round passive income.

BUILDINGS (3 total):
  Market:  wood=2 + stone=2  → +3 VP
  Granary: grain=3 + wood=1  → +3 VP + 2 grain/round passive income
  Tower:   stone=2 + clay=2  → +3 VP

ACTIONS this round (pick one):
  TRADE → initiate a proposal to one agent (you give X, you want Y from them)
  BUILD → spend resources to construct a building and gain VP
  HOARD → gain +2 specialty resource (vs +1 passive this round)
  GIFT  → give resources to an agent freely (builds goodwill, no immediate return)

TRADE MARKET:
  Before acting, all agents broadcast their needs publicly.
  Check the market board to find agents who want what you have.
  Counter-propose if an incoming offer is close but not right.

PENALTIES:
  Starvation: grain=0 at round end → -1 VP that round
  Spoilage: grain/fiber >3 units → excess decays (you lose the surplus)
  Destitution: all non-grain resources = 0 → -1 VP that round"""

RULES_BLOCK_COMPACT = """Trade Island v2: First to 10VP wins (25 rounds).
Resources: wood stone grain clay fiber. Eat 1 grain/round (0 grain→-1VP).
Grain+fiber spoil if >3 held. All non-grain=0→destitution -1VP.
Production: +1 specialty/round passive; HOARD=+2 specialty.
Buildings: Market(w2+s2→3VP) Granary(g3+w1→3VP+2grain/rnd) Tower(s2+c2→3VP).
Actions: TRADE BUILD HOARD GIFT. Market board shows who wants what."""
```

## agent_action.py v2 key changes

- System: import RULES_BLOCK_COMPACT, add to static system
- User message additions:
  - `Specialty: {specialty} (passive +1/rnd; HOARD=+2 this round)`
  - `MARKET BOARD: {rendered broadcasts from market_board}`
  - `RECENT EVENTS: bullet list from short_term_memory`
- JSON schema: add gift action: `{"action_type":"gift","target":str,"give":{...},"note":str}`
- grain_rounds_left: compute as `grain // max(1, hunger_rate - grain_income)` for accurate net

## trade_response.py v2 key changes

- System (STATIC — no dynamic values):
  ```python
  _SYSTEM = (
      "Trade Island v2. You are responding to a trade proposal. "
      + RULES_BLOCK_COMPACT
      + " ACCEPT if trade helps you reach a building or gives you a scarce resource. "
      "COUNTER with better terms if close. DECLINE only if trade hurts survival. "
      'JSON:{"accepted":true|false,"counter":{"wood":N,...}|null,"reason":"1 sentence"}'
  )
  ```
- User message additions:
  - Round number and rounds remaining: `R{N}/25 ({25-N} rounds left)`
  - Proposer context: `{proposer} (vp={v}, grain={g}, built={buildings}) offered this because they saw you broadcast {broadcast_hint}`
  - Path to next building: `You need {missing} for {target_building}` (computed from inventory)
  - Counter schema: sparse (not all-5-zeroes): `counter: {resource: qty} | null`

## reflection.py v2 key changes

- System: import RULES_BLOCK, include full rules
- Output: structured JSON not prose:
  ```
  JSON: {
    "survival_plan": "1 sentence",
    "next_building": "Market|Granary|Tower|none",
    "best_trade_target": "agent_id",
    "trade_strategy": "1 sentence",
    "relationships": {"a0": "cooperative|neutral|hostile", ...}
  }
  ```
- Pass event_log (last 10 events) to reflection for context

## Tests (test_prompts_v2.py)

```python
def test_rules_block_contains_win_condition():
    assert '10 VP' in RULES_BLOCK
    assert '10 VP' in RULES_BLOCK_COMPACT

def test_rules_block_contains_all_actions():
    for action in ['TRADE', 'BUILD', 'HOARD', 'GIFT']:
        assert action in RULES_BLOCK

def test_rules_block_contains_spoilage():
    assert 'spoil' in RULES_BLOCK.lower()

def test_respond_system_is_static():
    # Build two respond messages with different agent states
    # Their system messages must be identical (enabling caching)
    msg1 = build_respond_messages('a0', {'wood':2}, 3, proposal, {})
    msg2 = build_respond_messages('a1', {'stone':5}, 7, proposal, {})
    assert msg1[0]['content'] == msg2[0]['content'], 'System message must be static'

def test_act_prompt_contains_specialty():
    msgs = build_act_messages(..., specialty='wood', ...)
    assert 'wood' in msgs[1]['content']  # specialty in user message

def test_act_prompt_contains_market_board():
    market = {'a1': {'want': {'grain': 2}, 'offer_hint': 'wood'}}
    msgs = build_act_messages(..., market_board=market, ...)
    assert 'MARKET' in msgs[1]['content']
    assert 'grain' in msgs[1]['content']

def test_act_token_budget():
    # Full prompt under 250 tokens (chars // 4)
    msgs = build_act_messages(...)
    total_chars = sum(len(m['content']) for m in msgs)
    assert total_chars // 4 <= 250

def test_reflection_prompt_produces_json_schema():
    msgs = build_reflect_messages(...)
    assert 'survival_plan' in msgs[0]['content']
    assert 'next_building' in msgs[0]['content']
```

## Done When
- `pytest tests/test_prompts_v2.py` passes
- Respond system message is identical across all agent calls (verified by test)
- RULES_BLOCK contains: win condition, all actions, spoilage, destitution, production rate
- act prompt shows specialty, hoard reward, market board
- Commit: `feat: prompt rebuild — RULES_BLOCK + all prompt modules v2 (S05/T04)`
