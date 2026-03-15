---
estimated_steps: 8
estimated_files: 4
---

# T04: Write game.py, run_game.py, test_smoke.py and run acceptance test

**Slice:** S02 — Trade Island Engine
**Milestone:** M001

## Description

Final integration task. Wires all 5 prior modules into a 25-round game loop, adds the CLI entry point, writes the smoke test that locks the schema contract, and runs the real acceptance test. Two correctness constraints from the research plan are enforced here: JSONL flush+fsync *before* checkpoint write (not after), and reflection *after* round_end (not before). The acceptance run hits the real Mistral API.

## Steps

1. Write `src/simulation/game.py` — `GameRunner(config: GameConfig)`:
   - `run_game() -> dict`: Initialize agents (one `Agent` per config entry), `GM`, `GameLogger` (`game_id = uuid.uuid4().hex[:8]`). Create `Path(f"data/raw/{game_id}").mkdir(parents=True, exist_ok=True)`.
   - Log `game_start` event with `game_id, config.config_name, model_assignments, seed`.
   - For each round 1..25:
     - Log `round_start`.
     - Phase 1: each agent calls `act()` → collect `action_type` and trade proposals.
     - Phase 2: for each trade proposal, call the target agent's `respond_to_trade()`.
     - Phase 3: call `gm.resolve_trades()` → execute accepted trades (update inventories).
     - Phase 4: process builds — if agent action is `"build"`, deduct costs from inventory, add VP delta, log `build` event.
     - Phase 5: grain consumption — deduct `hunger_rate` grain per agent; if agent has 0 grain, apply damage penalty (log `grain_consumption` event).
     - **Flush sequence (order is critical):** call `logger.flush()` (fsync), THEN write `checkpoint_r{N:02d}.json` with full game state dict. Never reverse this order.
     - Log `round_end` via `logger.log_round_end(round_num, agents)` — one line per agent.
     - **After round_end:** if `round_num % 5 == 0`, call `agent.reflect()` for each agent, log `reflection` events.
   - After round 25: log `game_end` with `game_id, winner (highest VP agent_id), final_vp dict, rounds_played=25, total_cost_usd`.
   - Return summary dict with `game_id, total_cost_usd, rounds_played`.

2. Write `scripts/run_game.py` — argparse CLI:
   - `--config` (str, required): named config or `pairwise-{A}-{B}`
   - `--games` (int, default 1): number of sequential games to run
   - Initialize `litellm.BudgetManager` with `max_budget=80.0` once at startup.
   - Loop: `GameRunner(GameConfig.from_name(args.config)).run_game()`. Print per-game summary to stdout.
   - Exit 0 on success, 1 on any unhandled exception (print traceback).

3. Write `tests/test_smoke.py` — 3-round mock game. Use `unittest.mock.patch("litellm.completion")` or the `mock_response` kwarg approach. Test cases:
   - `test_round_end_schema`: run 3-round mock game, load all `round_end` lines from JSONL, assert each has keys `game_id, model_family, round, agent_id, vp`, assert `vp` is an int, assert `round_end` count == `num_agents * 3`.
   - `test_gm_resolution_schema`: assert at least one `gm_resolution` event exists in the JSONL, assert it has `accepted` field.
   - `test_checkpoint_exists`: assert `checkpoint_r01.json` exists after 3-round run.
   - `test_mock_cost_zero`: assert `game_end.total_cost_usd == 0.0` (not None) after full mock run.
   - `test_double_spend_in_game`: construct a scenario where two agents both propose trades consuming the same proposer resource; assert the second trade's `gm_resolution` has `valid=False`.
   - **Critical:** do NOT import `src.analysis.*` anywhere in this file — polars imports in analysis stubs will fail if polars is not installed in this exact test run order.

4. Run `pytest tests/test_smoke.py -v`. All tests must pass before step 5.

5. Run the real acceptance test: `python scripts/run_game.py --config mistral-mono --games 1`. Wait for completion (~25 rounds × ~6 agents × Mistral calls).

6. Verify output JSONL. Run these grep checks and confirm all pass:
   - `grep '"event": "round_end"' data/raw/*/game.jsonl | wc -l` → 150
   - `grep '"event": "game_end"' data/raw/*/game.jsonl` → shows `total_cost_usd` field
   - `grep '"accepted": true' data/raw/*/game.jsonl | head -1` → ≥1 result
   - `grep '"vp"' data/raw/*/game.jsonl | head -1` → confirms field name
   - Manually inspect `game_end` line: `total_cost_usd ≤ 0.02`

7. Update `src/simulation/__init__.py` to export `GameConfig`, `GameLogger`, `GameRunner`.

8. Run `pytest tests/test_smoke.py -v` one final time after the real game run to confirm no state leakage between test and live run.

## Must-Haves

- [ ] JSONL `flush()+fsync()` called before `checkpoint_r{N:02d}.json` is written — confirmed by code review of the round-end sequence in `game.py`
- [ ] `reflect()` called only after `log_round_end()` in the round loop — confirmed by code order in `game.py`
- [ ] `pytest tests/test_smoke.py` passes all 5 test cases
- [ ] `game_end.total_cost_usd` is `0.0` in mock run (not `None`) — `test_mock_cost_zero` passes
- [ ] Real 25-round game produces exactly 150 `round_end` lines (25 rounds × 6 agents)
- [ ] ≥1 `gm_resolution` event with `accepted=true` in real game JSONL
- [ ] `total_cost_usd ≤ 0.02` in real `game_end` event
- [ ] `src.analysis` is NOT imported in `tests/test_smoke.py`

## Verification

- `pytest tests/test_smoke.py -v` — all green
- `grep '"event": "round_end"' data/raw/*/game.jsonl | wc -l` → 150
- `python -c "import json; lines=[json.loads(l) for l in open(max(__import__('glob').glob('data/raw/*/game.jsonl')))]; end=[l for l in lines if l['event']=='game_end'][0]; assert end['total_cost_usd'] <= 0.02, f'cost {end[\"total_cost_usd\"]} exceeds 0.02'; print(f'cost ok: ${end[\"total_cost_usd\"]:.4f}')"` prints `cost ok`
- `grep '"accepted": true' data/raw/*/game.jsonl | wc -l` → ≥1

## Observability Impact

- Signals added/changed: `game_start` / `round_start` / `round_end` / `game_end` events form a complete recoverable audit trail; `total_cost_usd` in `game_end` is the primary cost signal
- How a future agent inspects this: `jq '.event' data/raw/*/game.jsonl | sort | uniq -c` gives event distribution; `jq 'select(.event=="game_end")' data/raw/*/game.jsonl` gives cost summary; `ls data/raw/{game_id}/checkpoint_r*.json` shows last checkpoint for resume
- Failure state exposed: game crash mid-round leaves JSONL with last-flushed state and the preceding checkpoint; a resume script can load the checkpoint and re-run the interrupted round cleanly (resume implementation deferred to S04, but the write ordering here is what makes it possible)

## Inputs

- `src/simulation/config.py` — `GameConfig.from_name()` from T01
- `src/simulation/logger.py` — `GameLogger` with `log_round_end()`, `flush()` from T01
- `src/simulation/llm_router.py` — `call_llm()` from T02
- `src/simulation/agent.py` — `Agent` class from T03
- `src/simulation/gm.py` — `GM` class with double-spend-safe `resolve_trades()` from T03
- `data/raw/` — directory exists (empty); `data/raw/{game_id}/` will be created by `game.py`

## Expected Output

- `src/simulation/game.py` — `GameRunner` class; 25-round loop with correct flush/checkpoint order
- `scripts/run_game.py` — CLI entry point; `$80` budget cap wired at startup
- `tests/test_smoke.py` — 5 test cases; all pass
- `src/simulation/__init__.py` — exports `GameConfig`, `GameLogger`, `GameRunner`
- `data/raw/{game_id}/game.jsonl` — real 25-round game log (150 round_end lines, ≥1 accepted trade)
- `data/raw/{game_id}/checkpoint_r{01..25}.json` — 25 checkpoint files
