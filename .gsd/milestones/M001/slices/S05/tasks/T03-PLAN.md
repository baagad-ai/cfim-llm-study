# T03: Broadcast Phase + Agent-Initiated Trade

**Slice:** S05 — Simulation Engine v2
**Status:** ⬜ Not started
**Est:** 1.5h

## Goal

Add the broadcast phase: before each agent acts, all agents declare what they want and what they can offer. This public market board is injected into every agent's act() prompt so proposals are targeted at agents who have signaled need — not cold-called blindly.

## Architecture

```
Round N:
  [Step 0] BROADCAST PHASE
    for agent in agents:
      broadcast = agent.broadcast(game_state)  # {want: {resource: qty}, offer_hint: str}
      broadcasts[agent.agent_id] = broadcast
      logger.log('broadcast', agent_id=..., model_family=..., want=..., offer_hint=...)
    
    # Update game_state with market board
    game_state = game_state_with_broadcasts(game_state, broadcasts)
  
  [Step 1] ACT PHASE (unchanged, but game_state now has market board)
    for agent in agents:
      action = agent.act(round_num, game_state)  # sees market board
```

## Files
- Modify: `src/simulation/agent.py` — add broadcast() method, update act() signature
- Modify: `src/simulation/engine.py` — add Step 0, update _build_game_state()
- Create: `src/prompts/broadcast.py` — build_broadcast_messages()
- Modify: `src/prompts/agent_action.py` — add market_board param, render in user message
- Create/modify: `tests/test_mechanics_v2.py` — broadcast tests

## Agent.broadcast() method

```python
def broadcast(
    self,
    game_state: dict,
    mock_response: str | None = None,
) -> dict:
    """Publicly declare what this agent wants to trade.
    
    Returns: {"want": {resource: qty}, "offer_hint": str}
    Logged as broadcast event. Shared with all agents before act() is called.
    """
    messages = build_broadcast_messages(
        agent_id=self.agent_id,
        inventory=self.inventory,
        vp=self.vp,
        buildings_built=self.buildings_built,
        specialty=self.specialty,
        game_state=game_state,
    )
    content, _cost = call_llm(
        model_string=self.model_string,
        provider=self.provider,
        messages=messages,
        mock_response=mock_response,
    )
    result = parse_agent_response(content, {})
    if result is None or 'want' not in result:
        return {'want': {}, 'offer_hint': 'unknown'}
    return result
```

## build_broadcast_messages() in broadcast.py

```python
# System (static):
# "Trade Island. Declare what you want to trade for this round.
# Output JSON: {\"want\": {\"resource\": qty}, \"offer_hint\": \"resource_name\"}
# want = resource you need most right now. offer_hint = resource you have surplus of."

# User (dynamic):
# "R{N}/25 You:{id} Specialty:{spec} Inv:{inventory} VP:{vp}
# Declare your trade need:"
```

## game_state update — add market_board

In `_build_game_state()` and new `_build_game_state_with_broadcasts()` in engine.py:
```python
game_state['market_board'] = {
    agent_id: {'want': broadcast.get('want', {}), 'offer_hint': broadcast.get('offer_hint', '')}
    for agent_id, broadcast in broadcasts.items()
}
```

## Tests

```python
def test_broadcast_returns_want_and_offer_hint():
    # Mock response: '{"want": {"grain": 2}, "offer_hint": "wood"}'
    # broadcast() returns {want: {grain: 2}, offer_hint: 'wood'}
    ...

def test_broadcast_fallback_on_parse_failure():
    # Mock response: 'invalid json'
    # broadcast() returns {want: {}, offer_hint: 'unknown'}
    ...

def test_market_board_visible_in_game_state():
    # After broadcast phase, game_state['market_board'] has entry for each agent
    ...

def test_act_prompt_includes_market_board():
    # build_act_messages() with non-empty market_board renders MARKET BOARD section
    ...
```

## Done When
- broadcast events appear in game JSONL
- market_board visible in game_state before act() calls
- act prompt shows MARKET BOARD section with agent declarations
- All broadcast tests pass
- Commit: `feat: broadcast phase + agent-initiated trade (S05/T03)`
