# T01: GameConfig v2 + GameState Dataclass

**Slice:** S05 — Simulation Engine v2
**Status:** ⬜ Not started
**Est:** 1h

## Goal

Add all new economy mechanics fields to GameConfig. Create GameState + AgentSnapshot dataclasses as the single immutable snapshot type for the round loop. Update config factories (win_vp=10). Move HUNGER_PENALTY_VP from game.py hardcode into config.

## Files
- Modify: `src/simulation/config.py`
- Create: `src/simulation/state.py`
- Create: `tests/test_config_v2.py`

## New GameConfig fields

```python
# Economy v2
hunger_penalty_vp: int = -1          # was hardcoded in game.py as _HUNGER_PENALTY_VP
win_vp: int = 10                     # lowered from implicit 12; 3 buildings = 9VP
base_production: int = 1             # specialty resource gained passively each round
hoard_bonus: int = 2                 # specialty resource gained when hoarding (vs base_production)

# Degradation
perishable_resources: list[str] = Field(default_factory=lambda: ["grain", "fiber"])
perishable_threshold: int = 3        # above this qty, resource decays by 1/round
destitution_penalty_vp: int = -1     # penalty if all non-grain resources = 0

# Architecture
broadcast_phase: bool = True         # run broadcast step 0 each round
stream_events: bool = True           # emit structured events (always True for now)
```

## GameState + AgentSnapshot (state.py)

```python
from dataclasses import dataclass, field
from typing import Any

@dataclass
class AgentSnapshot:
    agent_id: str
    model_family: str
    vp: int
    inventory: dict[str, int]
    buildings_built: list[str]
    specialty: str | None
    last_broadcast: dict | None  # {want: {...}, offer_hint: str} or None

@dataclass
class GameState:
    game_id: str
    config_name: str
    round: int
    num_rounds: int
    agents: list[AgentSnapshot]
    recent_events: list[dict]    # last 3 rounds of events (short-term memory)
    buildings: dict[str, Any]
    resources: list[str]
    win_vp: int
```

## Steps

1. Read `src/simulation/config.py` to understand current structure
2. Add new fields to GameConfig (with Field defaults for lists)
3. Update all _mono(), _mixed_4family(), _pairwise() factories to set win_vp=10 explicitly
4. Create `src/simulation/state.py` with AgentSnapshot and GameState
5. Write `tests/test_config_v2.py`:
   - test: new fields have correct defaults
   - test: from_name('mistral-mono') has win_vp=10
   - test: GameState can be constructed and accessed
   - test: perishable_resources defaults to [grain, fiber]
6. Run `pytest tests/test_config_v2.py -v` — all pass
7. Commit: `feat: GameConfig v2 + GameState dataclass (S05/T01)`

## Done When

- `pytest tests/test_config_v2.py` passes
- All new fields present with correct defaults
- GameState + AgentSnapshot importable from src.simulation.state
- `_HUNGER_PENALTY_VP` removed from game.py / engine.py
