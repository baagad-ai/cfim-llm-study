# T05: Memory System + Observability

**Slice:** S05 — Simulation Engine v2
**Status:** ⬜ Not started
**Est:** 1.5h

## Goal

Replace noisy prose memory with structured event injection. Compute RoundMetrics per round. Add full inventory to round_end events. Optional rich dashboard.

## Files
- Modify: `src/simulation/agent.py` — short_term_memory, structured reflection storage
- Modify: `src/simulation/engine.py` — RoundMetrics computation, event injection, round_end inventory
- Modify: `src/simulation/logger.py` — add inventory to round_end events
- Create: `src/observability/__init__.py`
- Create: `src/observability/metrics.py`
- Create: `src/observability/dashboard.py`
- Create: `tests/test_observability.py`

## Short-Term Memory (last 3 rounds of events)

```python
# In Agent:
short_term_memory: list[dict] = field(default_factory=list)  # last 3 rounds of events
# Each entry: {round: N, events: ["a1 accepted wood→grain trade", "a2 built Market", ...]}

# In engine.py — after each round:
for agent in agents:
    round_summary = _summarize_round_events(agent.agent_id, round_events)
    agent.short_term_memory.append({'round': round_num, 'events': round_summary})
    agent.short_term_memory = agent.short_term_memory[-3:]  # keep last 3 rounds only

# In build_act_messages() — injected as:
recent_events = "\n".join(
    f"  r{e['round']}: " + " | ".join(e['events'][:3])
    for e in short_term_memory[-3:]
)
```

## Structured Reflection Storage

```python
# agent.reflect() now stores a dict, not a string:
# {survival_plan: str, next_building: str, best_trade_target: str, trade_strategy: str, relationships: dict}
# memory: list[dict | str] — backward compatible (old games have strings)

# In build_act_messages() — reflections rendered as structured bullets:
mem_bullets = []
for m in memory[-2:]:
    if isinstance(m, dict):
        mem_bullets.append(f"  → Build: {m.get('next_building','?')} | Trade: {m.get('trade_strategy','?')}")
    else:
        mem_bullets.append(f"  → {str(m)[:80]}")
```

## RoundMetrics

```python
# src/observability/metrics.py

@dataclass
class RoundMetrics:
    round: int
    gini: float                    # VP Gini coefficient
    trade_acceptance_rate: float   # accepted / proposed this round (0 if no proposals)
    cumulative_trade_rate: float   # accepted / proposed all rounds so far
    avg_vp: float
    vp_std: float
    avg_resource_diversity: float  # mean Shannon entropy of agent inventories
    broadcast_count: int
    gift_count: int
    starvation_count: int
    spoilage_count: int
    destitution_count: int

def compute_round_metrics(
    round_num: int,
    agents: list,
    round_proposals: list,
    round_accepted: int,
    total_proposals: int,
    total_accepted: int,
    round_events: list[dict],
) -> RoundMetrics:
    vps = [a.vp for a in agents]
    gini = _gini(vps)
    avg_vp = sum(vps) / len(vps)
    vp_std = (sum((v - avg_vp)**2 for v in vps) / len(vps)) ** 0.5
    trade_rate = round_accepted / max(1, len(round_proposals))
    cum_rate = total_accepted / max(1, total_proposals)
    diversity = sum(_shannon_entropy(a.inventory) for a in agents) / len(agents)
    ...
```

## Round-End Inventory (logger.py change)

```python
# Current log_round_end() only logs vp per agent.
# v2: include full inventory.
def log_round_end(self, round_num: int, agent_states: list[dict]) -> None:
    # agent_states now includes: {agent_id, model_family, vp, inventory, buildings_built}
    for state in agent_states:
        self.log('round_end',
                 round=round_num,
                 agent_id=state['agent_id'],
                 model_family=state['model_family'],
                 vp=state['vp'],
                 inventory=state['inventory'],          # NEW
                 buildings_built=state.get('buildings_built', []),  # NEW
        )
```

## Optional Rich Dashboard (dashboard.py)

```python
# Only imported/used if config.dashboard == True
# Uses rich.live.Live + rich.table.Table
# Shows:
#   - Per-agent row: agent_id | model | VP/10 | grain | wood/stone/clay/fiber | buildings
#   - Round N/25 | trades this round | acceptance rate | total cost
# Updates at end of each round (not per-LLM-call, to avoid flicker)
```

## Tests (test_observability.py)

```python
def test_round_metrics_gini_zero_for_equal_vp():
    # All agents vp=5 → gini = 0
    ...

def test_round_metrics_trade_rate():
    # 3 proposals, 1 accepted → trade_acceptance_rate = 0.333
    ...

def test_round_end_includes_inventory():
    # Run mock game, check round_end events have 'inventory' field
    ...

def test_short_term_memory_capped_at_3_rounds():
    # Append 5 round summaries, verify len = 3
    ...

def test_structured_reflection_stored_as_dict():
    # Mock reflect() response: valid JSON with survival_plan etc.
    # Verify agent.memory[-1] is a dict
    ...
```

## Done When
- round_metrics events in JSONL (verify with jq)
- round_end events include inventory dict
- short_term_memory appended per round, capped at 3
- Structured reflection stored as dict in agent.memory
- All observability tests pass
- Commit: `feat: memory system + RoundMetrics observability (S05/T05)`
