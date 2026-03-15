# S02: Concordia v2.0 Integration + Trade Island

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 1-2 weeks (varies on marketplace evaluation)
**Requirements:** R002, R011

## Goal

Concordia v2.0 running Trade Island simulations. Per-round JSONL logs. Checkpoint saves. GM resolution working.

## Tasks

### T01: Concordia v2.0 marketplace evaluation
- Read Concordia v2.0 docs and source for built-in marketplace/economy components
- Answer: Does the built-in marketplace support:
  - Resource inventory per agent?
  - Bilateral trade proposals (agent A offers X to agent B for Y)?
  - GM validation layer (sequential resolution, double-spending prevention)?
  - Per-round VP tracking?
- Decision: reuse built-in (saves weeks) OR build custom Trade Island components
- Document decision in DECISIONS.md as D019+

### T02: Trade Island component implementation
- `TradeIslandAgent`: Entity with resource inventory (W, S, G, Wo, O, C), VP counter, specialty assignment, reflection memory
- `TradeIslandGM`: Sequential trade resolver with double-spending prevention. Input: accepted trade list + inventory matrix. Output: valid/invalid per trade with reason.
- `TradeIslandGame`: 25-round orchestrator. Simultaneous phase (all agents propose simultaneously), sequential GM resolution, building phase, grain consumption phase.
- Resource specialty assignment: randomized at game start, recorded as metadata covariate

### T03: Per-agent LLM override wiring
- Use Concordia v2.0 native per-agent LLM override feature
- Monoculture games: all 6 agents → same model
- Pairwise games: 3 agents → model A, 3 agents → model B
- Verify: each agent call routes to correct provider, costs tracked separately

### T04: Checkpoint system
- Save game state after every round to `data/raw/{game_id}/round_{n}.json`
- State includes: round number, all agent inventories, VP counts, event log
- Resume from checkpoint on crash
- Test: kill process mid-game, resume, verify correct continuation

### T05: JSONL structured logging
- Per-game log file: `data/raw/{game_id}/game.jsonl`
- Each line is one event: round start, agent decision, trade proposal, trade response, GM resolution, building action, grain consumption, reflection, round end, game end
- Schema per event type defined in `src/simulation/log_schema.py`
- Validate schema on every write (Pydantic models)

### T06: Single-game smoke test
- Run one complete 25-round game (all Mistral agents — cheapest)
- Verify: 25 rounds complete, JSONL log valid, checkpoint files exist, total cost ≤ $0.02
- Manual inspection: does agent behavior make sense? Are trades happening? Are VPs accumulating?

## Acceptance Criteria

- [ ] Concordia v2.0 marketplace evaluation documented (DECISIONS.md D019)
- [ ] Single 25-round game completes end-to-end
- [ ] JSONL log validates against schema (all 25 rounds × 6 agents events)
- [ ] Checkpoint: crash-resume works (tested by killing mid-round and resuming)
- [ ] Per-agent LLM routing verified (costs attributed correctly per model)
- [ ] Cost: one smoke test game ≤ $0.02

## Notes

- Simultaneous engine: all 6 agents submit actions in the same "tick" — no information leakage between agents within a round
- GM resolves trades SEQUENTIALLY to prevent double-spending (process trade 1, update inventories, then process trade 2)
- Grain consumption at END of round (not start) — agents must plan for it
- VP values are equal (all structures = 3VP) per blueprint §3 fix
