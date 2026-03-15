# Trade Island Simulation Engine v2 — Design Document

**Date:** 2026-03-15  
**Status:** APPROVED — basis for implementation plan  
**Supersedes:** SIMULATION_AUDIT.md (root cause analysis) + S04 repair sprint

---

## Problem Statement

The current engine produces scientifically invalid data. Every game ends with all agents at −17 to −20 VP. Trade acceptance is 0%. The winner is whoever starves least — which measures nothing about cooperation, strategy, or model behavioral differences. H1–H4 are untestable.

**Three compounding root causes:**
1. **Broken economy:** Net grain income = 0, resources don't regenerate, no degradation pressure → no urgency to trade
2. **Blind agents:** Agents don't see the win condition, their own specialty, or why trades are mutually beneficial → 0% acceptance
3. **No observability:** Silent failures, unstructured memory, no event streaming → can't debug or analyze

**User directive:** Rebuild from first principles. Trade initiated by agents. Real degradation. Complex mechanics. Agents have full rules + memory access. Fully observable, tracked, streamed simulation.

---

## First-Principles Game Design

### Why Agents Trade In Real Economic Games (Catan Model)

Trades happen in Catan because **resource specialization creates asymmetric need**:
- You produce wheat and ore; your neighbor produces wood and brick
- You literally cannot build without trading — the game is *mathematically unwinnable* without it
- The player who refuses to trade falls behind deterministically

Our current game lacks this. Starting inventories are slightly differentiated but:
1. Agents don't know their specialty or others' specialties
2. All buildings require the same 2-resource pairs, so any agent can build any building from starting inventory
3. There's no mechanic that increases scarcity over time

### Degradation As Strategic Driver

Real urgency comes from **resource decay + survival economics**:
- If resources decay, hoarding becomes irrational — trade before it rots
- If production of building materials requires consuming other resources, agents must specialize and trade
- If multiple resources can trigger penalties (not just grain), agents have more reasons to seek trades

### Agent-Initiated Trade (vs Responder-Passive Trade)

Current architecture: proposer picks action_type=trade, names target, makes offer. Responder either accepts or declines. This is "cold call" trading — the proposer has no signal that the responder wants anything.

Better architecture: **broadcast + match**:
1. All agents broadcast their "want" publicly (what they're short of)
2. Agents who can satisfy a broadcast initiate targeted proposals
3. The responder already knows the proposer read their broadcast → higher acceptance rate
4. Creates a genuine market: public demand signals + private supply decisions

This mirrors actual markets and creates observable behavioral patterns (who broadcasts strategically vs truthfully, who exploits desperate broadcasters, who cooperates across family lines).

---

## v2 Game Mechanics (First Principles)

### Economy Model

**Resource production (NEW):**
- Every agent produces their specialty resource at +1/round automatically (base production)
- Hoard action: +2 specialty resource instead of +1 (active production bonus)
- Granary effect: +2 grain/round (already exists, keep it)
- This creates surplus → trade incentive (you have more than you need of your specialty)

**Resource consumption / degradation (NEW):**
- Grain: hunger_rate=1/round (keep existing)
- Perishables (grain, fiber): decay by 1/round if held > 3 units (spoilage mechanic)
  - Incentive: trade surplus grain/fiber before it spoils; don't hoard
- Non-perishables (wood, stone, clay): no decay (they're durable)
  
**VP mechanics (improved):**
- Buildings: Market(+3VP), Tower(+3VP), Granary(+3VP, +2grain/rnd) — keep
- Win condition: first to 10VP wins (lowered from 12; 3 buildings = 9VP + 1 grain bonus = possible)
- End-of-game scoring: VP at round 25 if no early win
- Early win: any agent reaching 10VP triggers game end at round boundary

**Starvation is multi-resource (NEW):**
- Grain=0: −1VP/round (existing, keep)
- All non-grain resources = 0 (total destitution): −1 VP that round (new penalty)
- This prevents the "I'm fine, I'll just sit on my starting inventory" equilibrium

### Agent Actions (v2)

Each round, agents take TWO steps:

**Step A — Broadcast (new):** Every agent publicly declares their want
```json
{"want": {"grain": 2}, "offer_hint": "wood"}
```
This is free (no cost), publicly visible to all agents, and doesn't commit them.

**Step B — Act (existing, enhanced):** Each agent chooses one of:
1. `trade`: Initiate a proposal to a SPECIFIC agent, citing their broadcast or private knowledge
   - Must name target, give resources, want resources, and optionally a `reason` (strategic context)
   - Can ALSO respond to incoming proposals (from Step C)
2. `build`: Spend resources to construct a building
3. `hoard`: Gain +2 specialty resource (active production bonus)
4. `gift`: Give resources to another agent with no ask (altruism / relationship building) — NEW
   - Records in relationship history; may influence future trade acceptance

**Step C — Trade Processing:** 
- All broadcasts are collected and shared with all agents (they see who wants what)
- Proposals go to targets; targets respond (accept/counter/decline)
- GM validates and executes accepted trades

### Memory and Rules Access (First Principles)

**What agents need to make rational decisions:**

1. **Game rules** (static, in system prompt):
   - All resources and what they do
   - All buildings and their costs + effects
   - Win condition (first to 10VP)
   - Starvation mechanic and rate
   - Spoilage mechanic (grain/fiber decay)
   - Their own specialty and production rate
   - Available actions and what each does

2. **Current state** (per round, in user message):
   - Own inventory (full)
   - Own VP and buildings built
   - Others' public signals: VP, grain level, buildings built, last broadcast
   - Round number and rounds remaining
   - Urgency signals: grain rounds left (accurate), spoilage warnings, VP gap to leader

3. **Short-term memory** (last 3 rounds of events):
   - Who proposed trades to you (and what)
   - Who accepted/declined your proposals
   - What was built last round
   - Who broadcast desperate needs

4. **Long-term memory** (strategic reflections every 5 rounds):
   - Compressed strategic notes: "a2 always declines wood trades, a3 is cooperative"
   - Relationship assessments per agent
   - Resource gap analysis

---

## Architecture: Simulation Engine v2

### Module Structure

```
src/simulation/
├── config.py          # GameConfig v2 — add production, decay, destitution fields
├── engine.py          # NEW: SimulationEngine — replaces game.py (cleaner name)
├── agent.py           # Agent v2 — add broadcast(), short_term_memory
├── gm.py              # GM (minimal changes — add gift validation)
├── logger.py          # GameLogger (add StreamHandler support — real-time)
├── state.py           # NEW: GameState dataclass — single source of truth
└── metrics.py         # NEW: RoundMetrics — computed per round, logged separately

src/prompts/
├── rules.py           # NEW: RULES_BLOCK constant — shared by all prompts
├── agent_action.py    # v2 — uses rules.py, adds specialty, broadcast context
├── broadcast.py       # NEW: build_broadcast_messages()
├── trade_response.py  # v2 — static system, full context, sponser motivation
├── reflection.py      # v2 — structured output format, event log access
└── json_utils.py      # (keep, minor additions)

src/observability/
├── stream.py          # NEW: SimulationStream — SSE/websocket event emitter
├── dashboard.py       # NEW: console dashboard (rich live display)
└── metrics_collector.py # NEW: RoundMetrics aggregator
```

### GameConfig v2 Fields (additions to current)

```python
class GameConfig(BaseModel):
    # ... existing fields ...
    
    # Economy
    hunger_penalty_vp: int = -1          # moved from hardcoded
    win_vp: int = 10                      # lowered from 12; 3 buildings achievable
    base_production: int = 1             # specialty resource produced per round (passive)
    hoard_bonus: int = 2                 # specialty resource gained when hoarding  
    
    # Degradation
    perishable_resources: list[str] = ["grain", "fiber"]   # these decay
    perishable_threshold: int = 3        # above this qty, excess decays each round
    destitution_penalty_vp: int = -1     # penalty for all-zero non-grain inventory
    
    # Agent-initiated trade
    broadcast_phase: bool = True         # whether to run broadcast step
    
    # Observability
    stream_events: bool = True           # emit events to StreamHandler
    dashboard: bool = False              # show rich live dashboard
```

### GameState Dataclass (NEW)

Single source of truth, immutable snapshot per round:

```python
@dataclass(frozen=True)
class AgentSnapshot:
    agent_id: str
    model_family: str
    vp: int
    inventory: dict[str, int]
    buildings_built: tuple[str, ...]
    specialty: str | None
    last_broadcast: dict | None         # what they declared wanting

@dataclass(frozen=True)  
class GameState:
    game_id: str
    config_name: str
    round: int
    num_rounds: int
    agents: tuple[AgentSnapshot, ...]
    round_events: tuple[dict, ...]       # events from last 3 rounds (short-term memory)
    buildings: dict                      # available buildings + costs
    resources: list[str]
    win_vp: int
    
    # Computed properties
    @property
    def leaderboard(self) -> list[tuple[str, int]]: ...
    @property  
    def grain_starved_agents(self) -> list[str]: ...
```

### Round Loop v2

```
Round N:
  [Step 0] Build GameState snapshot
  
  [Step 1] BROADCAST PHASE (NEW)
    - Each agent calls broadcast(game_state) → {want: {...}, offer_hint: str}
    - Broadcasts are public; all agents see them before acting
    - Game state is updated with broadcasts (public market board)
  
  [Step 2] ACTION PHASE
    - Each agent calls act(game_state_with_broadcasts) → one of:
        trade: {target, give, want, reason}
        build: {building}
        hoard: {}
        gift:  {target, give, note}
    - Actions logged with full payload
  
  [Step 3] TRADE RESOLUTION
    - All trade proposals collected
    - Targets respond: respond_to_trade(proposal, game_state)
    - GM validates (double-spend safe, inventory checks)
    - Accepted trades executed on real inventories
    - All outcomes logged (accepted, declined, countered, invalidated)
  
  [Step 4] BUILD RESOLUTION
    - Build actions processed
    - Affordability checked
    - Buildings applied to agent state + VP updated
    - build/build_failed events logged
  
  [Step 5] GIFT RESOLUTION (NEW)
    - Gifts applied to inventories (no validation needed beyond sender has resources)
    - Relationship history updated
    - gift event logged
  
  [Step 6] PRODUCTION (RENAMED from "hoard SF9")
    - Base production: every agent gains +1 specialty resource
    - Hoard bonus: agents who hoarded gain +2 (net +2 vs base +1)
    - production events logged per agent
  
  [Step 7] GRAIN ECONOMY
    - Grain income: +1/round to all agents (keep)
    - Grain consumption: −1/round
    - Starvation check: grain=0 → −1VP
    - grain_consumption events logged
  
  [Step 8] SPOILAGE (NEW)
    - For each perishable resource (grain, fiber):
      if agent.inventory[res] > perishable_threshold:
        agent.inventory[res] = perishable_threshold  (or -1 decay)
    - spoilage events logged
  
  [Step 9] DESTITUTION CHECK (NEW)
    - If all non-grain resources = 0: −1VP penalty
    - destitution events logged
  
  [Step 10] EARLY WIN CHECK
    - If any agent >= win_vp: game ends
  
  [Step 11] METRICS COMPUTATION (NEW)
    - RoundMetrics computed: gini, trade_rate, avg_vp, resource_diversity, etc.
    - Emitted to stream + logged
  
  [Step 12] CHECKPOINT + FLUSH
    - JSONL fsync (existing order, keep)
    - Checkpoint JSON written
    - round_end logged with full inventory per agent
  
  [Step 13] REFLECTION (rounds 5/10/15/20/25)
    - Agents reflect with event log access (not just current state)
    - Structured output: {survival_plan, next_building, target_agent, reason}
    - Reflection stored as structured dict (not raw prose)
```

### Prompt Architecture v2

**Shared RULES_BLOCK (static — in rules.py):**

```
TRADE ISLAND v2 RULES
======================
GOAL: First to 10 VP wins. Game ends at round 25 if no winner.

RESOURCES (5 types):
  wood, stone, grain, clay, fiber
  • Grain: consumed 1/round. grain=0 → -1VP that round.
  • Grain/fiber: spoil if held >3 units (excess decays each round). Trade before they rot.
  • All other resources: durable (no decay).

PRODUCTION:
  • Each round, you automatically gain +1 of your specialty resource.
  • HOARD action: gain +2 specialty instead (active production mode).
  • Granary building: +2 grain/round bonus.

BUILDINGS (3 total, all cost varies):
  Market:  wood=2 + stone=2  → +3 VP
  Granary: grain=3 + wood=1  → +3 VP + 2 grain/round passive income
  Tower:   stone=2 + clay=2  → +3 VP

ACTIONS (pick one per round):
  TRADE  → initiate proposal to another agent (give X, want Y, name target)
  BUILD  → spend resources to construct a building
  HOARD  → gain +2 specialty resource (vs passive +1)
  GIFT   → give resources to an agent, no ask (builds goodwill)

TRADE MARKET:
  Before acting, all agents broadcast what they want publicly.
  Use broadcasts to find willing trading partners.
  You can counter-propose if the offer isn't quite right.

PENALTIES:
  Starvation: grain=0 at round end → -1 VP
  Destitution: all non-grain resources = 0 → -1 VP
```

**Agent Act Prompt (user message, per round):**

```
R{N}/25 | You:{id} Specialty:{spec} (gain +1/rnd, +2 if hoard)
VP:{vp}/10 | Built:{buildings}
INV: wood={w} stone={s} grain={g} clay={c} fiber={f}
⚠ grain runs out in {accurate_rounds} rounds | {spoilage_warnings}

MARKET BOARD (broadcasts):
  {a1}: wants {grain=2}, has surplus {wood}
  {a2}: wants {stone=1}, has surplus {fiber}
  ...

OTHERS:
  {a1}: vp={v} grain={g} built={buildings}
  ...

RECENT EVENTS (last 3 rounds):
  r{N-1}: a3 declined your wood→grain offer | a1 accepted grain→stone | a2 built Market
  r{N-2}: you hoarded +2 wood | a0 broadcast grain need
  r{N-3}: ...

STRATEGY NOTES (your reflections):
  {reflection_summary_1}
  {reflection_summary_2}

Action? JSON: {"action_type":"trade"|"build"|"hoard"|"gift", ...}
```

**Trade Response Prompt (static system + dynamic user):**

SYSTEM (fully static — cache-friendly):
```
TRADE ISLAND v2. You are responding to a trade proposal.
Rules: [RULES_BLOCK condensed]
ACCEPT if it moves you toward a building or gives you a resource you need.
COUNTER if the offer is close but not quite right.
DECLINE only if the trade hurts your survival.
JSON: {"accepted": true|false, "counter": {"wood":N,...} | null, "reason": "1 sentence"}
```

USER (dynamic):
```
You:{id} Specialty:{spec} VP:{vp}/10 R{round}/25
INV: wood={w} stone={s} grain={g} clay={c} fiber={f}
Built: {buildings} | Grain runs out: {accurate_rounds} rounds

PROPOSAL from {proposer} (vp={proposer_vp}, built={proposer_buildings}):
  They give: {give_resources}
  They want: {want_resources}
  Their broadcast said: "{proposer_broadcast}"

Your path to next building: need {missing_resources} for {target_building}
Accept?
```

**Reflection Prompt (structured output):**

```
REFLECT on rounds {start}–{N}:
EVENTS: [last 10 events as compressed bullet list]
YOUR STATE: VP={vp} INV={inv} Built={buildings}

Output JSON:
{
  "survival_plan": "1 sentence grain/resource plan",
  "next_building": "Market|Granary|Tower|none",
  "best_trade_target": "agent_id",
  "trade_strategy": "1 sentence on why and what to offer",
  "relationships": {"a1": "cooperative|neutral|hostile", ...}
}
```

### Observability Architecture

**Event Stream (real-time):**
- Every event emitted to a `SimulationStream` that supports:
  - File JSONL (existing)
  - Console stdout (existing, one line per round)
  - **Rich dashboard** (new, optional): live terminal UI with VP bars, trade stats, inventory heatmap
  - **Server-Sent Events** (optional): stream to http://localhost:8765 for browser visualization

**Structured Events (v2 contract):**
All events have: `{event_type, game_id, round, timestamp, ...fields}`

New/enhanced events:
- `broadcast`: {agent_id, model_family, want, offer_hint, round}
- `trade_proposal`: {proposer, responder, give, want, reason, round}
- `trade_response`: {agent_id, accepted, counter, reason, round}
- `gift`: {giver, receiver, resources, note, round}
- `production`: {agent_id, resource, amount, action_source: "passive"|"hoard", round}
- `spoilage`: {agent_id, resource, amount_decayed, new_amount, round}
- `destitution`: {agent_id, vp_penalty, round}
- `round_metrics`: {round, gini, trade_acceptance_rate, avg_vp, resource_diversity_index}
- `round_end`: {round, agents: [{agent_id, vp, inventory, buildings_built, ...}]}  (full inventory NOW)

**RoundMetrics (computed per round):**
```python
@dataclass
class RoundMetrics:
    round: int
    gini: float                        # VP inequality
    trade_acceptance_rate: float       # accepted / proposed this round
    cumulative_trade_rate: float       # accepted / proposed all rounds
    avg_vp: float
    vp_std: float
    avg_resource_diversity: float      # Shannon entropy of per-agent inventories
    broadcast_count: int
    gift_count: int
    starvation_count: int
    spoilage_count: int
    destitution_count: int
    model_vp: dict[str, float]         # avg VP by model family this round
```

---

## What This Fixes

| Problem | Fix |
|---|---|
| 0% trade acceptance | Broadcasts create context; proposer motivation visible; structured acceptance framing |
| −17 to −20 VP | Passive production (+1 specialty/round); lower win VP (10); meaningful buildings |
| Hoard is a no-op | Hoard = +2 specialty (vs +1 passive) — meaningful production choice |
| No degradation | Spoilage (grain/fiber decay above threshold); destitution penalty |
| Trade not agent-initiated | Broadcast phase: agents declare needs → targeted proposals follow naturally |
| Agents don't know rules | RULES_BLOCK shared across all prompts; win condition explicit; mechanics named |
| Agents can't remember | Structured short-term events (last 3 rounds) + structured reflection JSON |
| Memory is noise | Reflections produce JSON not prose; stored as structured dict; compressed on ingest |
| No observability | RoundMetrics per round; full inventory in round_end; rich console dashboard |
| Silent build failures | build_failed logged with reason + inventory (already partially done) |

---

## Roles Required for Implementation

This redesign spans 5 independent domains. We'll use parallel agents.

### Role 1: Economy Mechanic Implementor
**Domain:** `config.py`, `engine.py` (game loop)  
**Scope:** New config fields, production/decay/destitution phases, win_vp lowering  
**Files:** `src/simulation/config.py`, `src/simulation/engine.py` (renamed from game.py)

### Role 2: Prompt Architect  
**Domain:** `src/prompts/`  
**Scope:** RULES_BLOCK, agent_action v2, broadcast prompt, trade_response v2 (static system), reflection v2 (structured JSON)  
**Files:** All files in `src/prompts/`

### Role 3: Agent & Memory Redesigner  
**Domain:** `src/simulation/agent.py`  
**Scope:** broadcast() method, act() with short_term_memory, reflect() with structured output, gift() method  
**Files:** `src/simulation/agent.py`, `src/simulation/state.py` (new)

### Role 4: Observability Engineer  
**Domain:** `src/observability/`  
**Scope:** RoundMetrics, SimulationStream, rich dashboard, full round_end inventory  
**Files:** All new files in `src/observability/`, `src/simulation/logger.py` updates

### Role 5: Test Engineer  
**Domain:** `tests/`  
**Scope:** Update/add tests for all new mechanics; end-to-end smoke test with mock responses  
**Files:** `tests/test_mechanics.py`, `tests/test_simulation_v2.py` (new)

---

## Estimated Impact on Research Validity

Expected outcomes after v2 rebuild:
- **VP range:** 3–9 per game (previously −20 to 0) → H1 testable
- **Trade acceptance:** 15–40% (previously 0%) → H2 testable  
- **Model differentiation:** Visible VP spread across families → H3/H4 testable
- **Scientific validity:** Games are winnable, have genuine strategic tension, and produce differentiable behavioral signals
