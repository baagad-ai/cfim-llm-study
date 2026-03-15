# S05: Simulation Engine v2 — Full Rebuild

**Goal:** Rebuild Trade Island simulation from first principles: agent-initiated trade via broadcast+match market, resource degradation (spoilage + destitution), complete rules in agent prompts, structured memory, and full round-level observability. Produce scientifically valid games with VP in 3–9 range and trade acceptance >15%.

**Demo:** `python scripts/run_game.py --config phase0 --games 5` shows VP in 3–9 range, trade acceptance >15%, round_metrics events in JSONL, and a rich dashboard. `pytest tests/` passes 0 failures.

**Supersedes:** S04/T03-FIX patch sprint. S04/T01 and S04/T02 artifacts (cost tracking, crash-resume, format decisions) remain valid and are preserved.

**Design doc:** `docs/plans/2026-03-15-simulation-engine-v2-design.md`

---

## Must-Haves

- GameConfig v2 with: base_production, hoard_bonus, win_vp=10, perishable_resources, perishable_threshold, destitution_penalty_vp, broadcast_phase, stream_events
- GameState dataclass — immutable per-round snapshot used by all agents
- Broadcast phase: every agent calls broadcast() → public market board in game_state before act()
- Agent-initiated trade: act() prompt shows market board; proposals are targeted based on declared need
- Hoard = +2 specialty (active) vs passive +1/round production for all agents
- Spoilage: grain/fiber > threshold → decay by 1 per round (logged as spoilage events)
- Destitution: all non-grain resources = 0 → −1VP (logged as destitution events)
- RULES_BLOCK: shared static rules constant imported by all prompt modules
- Complete act prompt: win condition, specialty, hoard reward, production rate, market board, structured recent events
- Complete respond prompt: static system (cache-friendly), full context (proposer motivation, round remaining, path to next building)
- Structured reflection: JSON output {survival_plan, next_building, best_trade_target, trade_strategy, relationships}
- RoundMetrics: gini, trade_acceptance_rate, avg_vp, vp_std computed per round, logged as round_metrics events
- round_end events include full inventory per agent
- Gift action: agents can gift resources with no ask (builds relationship history)
- `pytest tests/` passes 0 failures (including new mechanics tests)
- 5-game validation confirms: VP 3–9, trade acceptance >15%, no starvation floor

## Proof Level

- This slice proves: operational (real API calls; real data produced)
- Real runtime required: yes — T06 5-game validation with live LLM calls
- Human/UAT required: yes — Go/No-Go for Phase 0 30-game run requires VP range and acceptance rate review

## Verification

```bash
# After T05: all tests pass
pytest tests/ -v
# → 30+ tests pass, 0 failures

# After T06: 5-game validation signal
for gid in $(ls -t data/raw | head -5); do
  jq 'select(.event=="game_end") | {winner_vp, total_cost_usd}' data/raw/$gid/game.jsonl
done
# VP: 3–9 range, no negatives

jq 'select(.event=="round_metrics") | {round, trade_acceptance_rate, gini}' \
  data/raw/$(ls -t data/raw | head -1)/game.jsonl | head -30
# round_metrics events present; trade_acceptance_rate > 0 in most rounds

grep '"event":"broadcast"' data/raw/*/game.jsonl | head -5
# broadcast events present — agents are declaring needs

grep '"event":"spoilage"' data/raw/*/game.jsonl | head -5
# spoilage events present — degradation mechanic is running

grep '"accepted": true' data/raw/*/game.jsonl | wc -l
# ≥ 7 accepted trades across 5 validation games (>15% of ~50 proposals per game × 5)
```

## Integration Closure

- Upstream surfaces consumed: S01 (LiteLLM routing), S02 (JSONL schema, checkpoint pattern), S03 (tolerant parser, json_utils), S04/T01 (cost tracking, crash-resume), S04/T02 (format decisions D041–D046)
- New surfaces produced: engine.py (replaces game.py), state.py, observability/, prompts/rules.py, prompts/broadcast.py
- What remains before M001 is complete: S06 (OSF pre-registration — was S05, renumbered)

---

## Tasks

- [ ] **T01: GameConfig v2 + GameState dataclass** `est:1h`
  - Add new config fields (base_production, hoard_bonus, win_vp, perishable_resources, perishable_threshold, destitution_penalty_vp, broadcast_phase, stream_events, hunger_penalty_vp moved from hardcode). Create GameState + AgentSnapshot dataclasses in state.py. Update config factories to set win_vp=10. Write unit tests.

- [ ] **T02: Economy mechanics — production, spoilage, destitution** `est:1.5h`
  - In engine.py (renamed from game.py): add passive production phase (+1 specialty/round), upgrade hoard to +2, add spoilage phase (grain/fiber decay above threshold), add destitution check, move HUNGER_PENALTY_VP to config. Log spoilage and destitution events. Write unit tests for each mechanic.

- [ ] **T03: Broadcast phase + agent-initiated trade** `est:1.5h`
  - Add Agent.broadcast() method + build_broadcast_messages() prompt. Add Step 0 to round loop: gather broadcasts → update game_state market board. Update Agent.act() to receive market board. Update build_act_messages() to show market board. Proposals now reference broadcaster's declared want. Write unit tests.

- [ ] **T04: Prompt rebuild — RULES_BLOCK + all prompt modules** `est:2h`
  - Create prompts/rules.py with RULES_BLOCK constant (complete rules: resources, buildings, actions, win condition, production, degradation). Rebuild agent_action.py v2 (specialty visible, hoard reward, market board, recent events structured). Rebuild trade_response.py v2 (static system, proposer motivation, round remaining, path to next building). Rebuild reflection.py v2 (structured JSON output). Add gift action to agent_action schema. Write prompt token budget tests.

- [ ] **T05: Memory system + observability** `est:1.5h`
  - Agent.short_term_memory: last 3 rounds of events as structured list, injected into act() prompt as recent events bullets. Structured reflection storage (JSON dict, not prose). RoundMetrics dataclass + computation after every round. Log round_metrics events. Add inventory to round_end events. Optional rich dashboard (dashboard=True in config). Write metrics tests.

- [ ] **T06: Integration tests + 5-game validation** `est:1h + 30m wall`
  - Update/write tests: test_mechanics_v2.py covering all new mechanics (broadcast, production, spoilage, destitution, gift, round_metrics, structured reflection). Run `pytest tests/ -v` — must pass 0 failures. Then run 5 live phase0 games. Verify: VP 3–9, trade acceptance >15%, broadcast events present, spoilage events present, round_metrics events present, cost per game ≤$0.30.

---

## Files Touched

### T01
- `src/simulation/config.py` — new fields, updated factories
- `src/simulation/state.py` — NEW: GameState + AgentSnapshot dataclasses
- `tests/test_config_v2.py` — NEW

### T02
- `src/simulation/engine.py` — renamed from game.py (or new file importing game.py); add production/spoilage/destitution phases
- `tests/test_mechanics_v2.py` — NEW (partial)

### T03
- `src/simulation/agent.py` — add broadcast() method, short_term_memory field
- `src/simulation/engine.py` — add broadcast step 0, update game_state builder
- `src/prompts/broadcast.py` — NEW: build_broadcast_messages()
- `tests/test_mechanics_v2.py` — add broadcast tests

### T04
- `src/prompts/rules.py` — NEW: RULES_BLOCK constant
- `src/prompts/agent_action.py` — v2: specialty, hoard, market board, recent events, gift schema
- `src/prompts/trade_response.py` — v2: static system, full context
- `src/prompts/reflection.py` — v2: structured JSON output
- `tests/test_prompts_v2.py` — NEW: token budgets, RULES_BLOCK coverage, static system test

### T05
- `src/simulation/agent.py` — short_term_memory injection, structured reflection storage
- `src/simulation/engine.py` — RoundMetrics computation, round_end inventory, dashboard hook
- `src/observability/__init__.py` — NEW
- `src/observability/metrics.py` — NEW: RoundMetrics dataclass + compute()
- `src/observability/dashboard.py` — NEW: optional rich Live() panel
- `src/simulation/logger.py` — add inventory to round_end events
- `tests/test_observability.py` — NEW

### T06
- `tests/test_mechanics_v2.py` — complete
- `scripts/run_game.py` — minor: wire dashboard flag if passed via CLI
