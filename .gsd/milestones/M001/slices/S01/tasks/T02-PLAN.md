---
estimated_steps: 7
estimated_files: 2
---

# T02: RNE Game Engine

**Slice:** S01 — RNE Engine + LLM Router
**Milestone:** M001

## Description

Core game loop for the Repeated Negotiated Exchange. 35 rounds, 10% decay, simultaneous proposals, perturbation at round 20, M1–M4 computed post-game. Tested with inline deterministic script before the CLI is wired in T03.

## Steps

1. Write `RNERunner` class in `src/simulation/rne_game.py`
2. Implement resource decay: `floor(resource * 0.9)` applied per agent per round after settlement
3. Implement simultaneous proposal protocol: both agents produce action JSON; check compatibility; handle one-propose/one-pass case with second `respond` call
4. Implement trade compatibility check and settlement
5. Implement perturbation at round 20: log `perturbation` event; switch scripted opponent strategy
6. Implement M1–M4 computation post-game
7. Write `summary.json` and `metadata.json`; inline `__main__` smoke test

## Must-Haves

- [ ] `RNERunner.run_session(config, mock_response=None) -> dict` returns summary dict and writes JSONL + summary.json + metadata.json
- [ ] Each round: simultaneous action collection → compatibility check → (if one pass) second `respond` call → trade execution or skip → decay → `round_end` logged for both agents
- [ ] Decay applied as `int(resource_qty * (1 - 0.10))` per resource per agent; applied AFTER trade settlement, BEFORE round_end log
- [ ] Perturbation fires exactly once at `config.perturbation_round` (default 20): logs `{"event":"perturbation","round":20,"type":"cooperative_to_defective"}` or reverse based on pre-perturbation cooperation rate
- [ ] M1 = `completed_trades / total_rounds` (float, 0.0–1.0)
- [ ] M2 = mean signed resource-value advantage per completed trade (agent_a minus agent_b in wood-equivalent units; wood=1, stone=1, grain=2, cloth=2)
- [ ] M3 = first round post-perturbation where agent changes action type relative to pre-perturbation modal action; None if no change detected
- [ ] M4 = rounds until 5-round rolling M1 returns to within 0.10 of pre-perturbation 5-round rolling M1; None if never recovers
- [ ] `summary.json` written with: session_id, family_a, family_b, condition, disclosure, framing, M1–M4, total_cost_usd, total_rounds, parse_failure_count
- [ ] `metadata.json` written with full config as dict + wall_clock_seconds

## Verification

- `python src/simulation/rne_game.py` — inline test runs 5 mock rounds; asserts: decay applied correctly after round 1 (verify specific resource value); perturbation fires at round 3 in 5-round test (set perturbation_round=3 in test config); trade executes when both proposals are compatible; summary.json written to tmp dir; prints "smoke: ok"

## Observability Impact

- `parse_failure` events logged with `raw[:200]` when `parse_rne_response` returns None (added in S02 — placeholder log in T02 is fine)
- `game_end` event always written in try/finally — even on crash, game_end is visible
- `total_cost_usd` in summary.json provides per-session cost signal

## Inputs

- `src/simulation/config.py` — `RNEConfig`
- `src/simulation/logger.py` — `GameLogger`
- `src/simulation/llm_router.py` — `call_llm` (uses mock_response in T02)
- `SIMULATION_DESIGN.md` §3.2–§3.4 for exact round flow and metric definitions

## Expected Output

- `src/simulation/rne_game.py` — `RNERunner` class with `run_session` method
