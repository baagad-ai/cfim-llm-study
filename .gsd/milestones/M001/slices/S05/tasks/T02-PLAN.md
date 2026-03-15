# T02: Economy Mechanics — Production, Spoilage, Destitution

**Slice:** S05 — Simulation Engine v2
**Status:** ⬜ Not started
**Est:** 1.5h

## Goal

Rebuild the game economy in engine.py (renamed/forked from game.py):
- Every agent gains +1 specialty resource passively each round
- Hoard action gives +2 specialty instead of +1 passive
- Grain/fiber decay if held above perishable_threshold (spoilage)
- All-zero non-grain inventory triggers destitution penalty
- win_vp sourced from config (not hardcoded)
- hunger_penalty_vp sourced from config (not hardcoded)

## Files
- Modify: `src/simulation/engine.py` (can keep game.py as alias or rename)
- Modify: `tests/test_mechanics_v2.py` (add production/spoilage/destitution tests)

## Round Loop Changes (Phase ordering)

```
[Step 6] PRODUCTION (after gift resolution)
  for agent in agents:
    # Passive production: always
    specialty = agent.specialty
    if specialty:
      agent.inventory[specialty] = agent.inventory.get(specialty, 0) + config.base_production
    # Hoard bonus: if agent's action was hoard
    if action_type == 'hoard':
      if specialty:
        agent.inventory[specialty] = agent.inventory.get(specialty, 0) + config.hoard_bonus
        # (net: hoard gives base_production + hoard_bonus = 1+2 = 3 total)
  logger.log('production', agent_id=..., resource=specialty, amount=..., source='passive'|'hoard')

[Step 7] GRAIN ECONOMY (unchanged)
  grain income → grain consumption → starvation check

[Step 8] SPOILAGE (new)
  for agent in agents:
    for res in config.perishable_resources:
      qty = agent.inventory.get(res, 0)
      if qty > config.perishable_threshold:
        decay = qty - config.perishable_threshold
        agent.inventory[res] = config.perishable_threshold
        logger.log('spoilage', agent_id=..., resource=res, amount_decayed=decay, new_amount=config.perishable_threshold)

[Step 9] DESTITUTION CHECK (new)
  for agent in agents:
    non_grain = {k:v for k,v in agent.inventory.items() if k != 'grain'}
    if all(v == 0 for v in non_grain.values()) and non_grain:
      agent.vp += config.destitution_penalty_vp
      logger.log('destitution', agent_id=..., model_family=..., vp_penalty=config.destitution_penalty_vp, vp=agent.vp)
```

## Tests to Write

```python
# test_mechanics_v2.py

def test_passive_production_applies_each_round():
    # Agent with specialty=wood, base_production=1
    # After one round production phase, wood += 1
    ...

def test_hoard_gives_bonus_production():
    # Agent with specialty=stone, base_production=1, hoard_bonus=2
    # Agent action = hoard
    # After production phase, stone += 1+2 = 3 total? No — net is:
    # passive +1 always, hoard adds another +2 → stone += 3 total for hoard round
    # vs +1 for non-hoard round
    ...

def test_spoilage_caps_perishables_at_threshold():
    # Agent has grain=7, perishable_threshold=3
    # After spoilage phase: grain=3, spoilage event logged with amount_decayed=4
    ...

def test_spoilage_does_not_affect_durable_resources():
    # Agent has wood=10, stone=8 — no spoilage (not perishable)
    ...

def test_destitution_triggers_vp_penalty():
    # Agent has inventory={grain:3, wood:0, stone:0, clay:0, fiber:0}
    # After destitution check: agent.vp decremented by destitution_penalty_vp
    ...

def test_destitution_does_not_trigger_if_any_non_grain_resource():
    # Agent has inventory={grain:3, wood:1, stone:0, clay:0, fiber:0}
    # wood=1 so not destitute — no penalty
    ...

def test_win_vp_from_config():
    # GameConfig win_vp=10 triggers early win when agent reaches 10
    ...
```

## Done When
- All new tests pass
- Production/spoilage/destitution events appear in game JSONL
- HUNGER_PENALTY_VP and early-win threshold read from config
- Commit: `feat: economy mechanics v2 — production, spoilage, destitution (S05/T02)`
