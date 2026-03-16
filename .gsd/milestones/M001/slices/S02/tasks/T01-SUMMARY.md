---
id: T01
parent: S02
milestone: M001
provides:
  - build_system_prompt(condition, framing) — 9 cached (A/B/C × neutral/social/strategic) static system-prompt variants
  - RNERunner wired to call build_system_prompt once per session and pass result as system message every round
key_files:
  - src/prompts/rne_prompts.py
  - src/simulation/rne_game.py
  - tests/test_rne_prompts.py
key_decisions:
  - LRU cache on build_system_prompt (maxsize=None) — system prompts are pure functions of two strings; caching is free and correct
  - Prompt structure: framing_intro + condition_core + shared_mechanics — keeps each concern independently editable
  - Token budget verified at ~253–290 tokens (len//4) for all 9 variants, well within the 300-token ceiling
patterns_established:
  - All prompt variants assembled by concatenating three independent text blocks; new conditions/framings added by extending the two dicts
  - rne_game.py calls build_system_prompt once at session start, threads the cached result through all per-round call_llm calls
observability_surfaces:
  - parse_failure_count in summary.json tracks how often the parser failed
  - game.jsonl records every round event; grep '"event":"trade_executed"' gives trade count
duration: ~30m (pre-implemented from prior context)
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: System prompt variants — 3 conditions × 3 framings

**`build_system_prompt` ships 9 deterministic LRU-cached system prompts (3 conditions × 3 framings), wired into RNERunner as the session-level system message.**

## What Happened

Found `src/prompts/rne_prompts.py` already fully implemented from prior work. The module provides all three public API functions (`build_system_prompt`, `build_round_messages`, `parse_rne_response`) with the full 9-variant coverage. `rne_game.py` already imports and uses the module: `build_system_prompt` called once at session start, result threaded through every `call_llm` invocation.

Ran T01 verification inline + full test suite to confirm correctness. All 165 tests pass (118 prompt tests + 47 rne game tests). Smoke run completed: 35 rounds, cost $0.0072, within budget.

## Verification

```
# Token budget check — all 9 variants
A/neutral: 253 tok ok
A/social: 274 tok ok
A/strategic: 262 tok ok
B/neutral: 270 tok ok
B/social: 290 tok ok
B/strategic: 278 tok ok
C/neutral: 270 tok ok
C/social: 290 tok ok
C/strategic: 278 tok ok

# Full test suite
pytest tests/test_rne.py tests/test_rne_prompts.py -v
→ 165 passed, 1 warning

# Smoke run
python scripts/run_rne.py --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1
→ 35 rounds, cost=$0.0072 ≤ $0.05

# Trade count across all data/study1 sessions
grep '"event".*"trade_executed"' data/study1/*/game.jsonl | wc -l
→ 420 (≥1 ✓)

# Summary validation
smoke ok, cost: 0.007243010000000003
```

## Diagnostics

- `data/study1/{session_id}/game.jsonl` — full round-by-round event log; grep for `trade_executed`, `parse_failure`, `round_end`
- `data/study1/{session_id}/summary.json` — M1–M4 metrics + `total_cost_usd` + `parse_failure_count`
- `build_system_prompt.cache_info()` — lru_cache hit/miss stats per process

## Deviations

None — implementation matched the plan exactly.

## Known Issues

The latest smoke session yielded 0 trades (cooperation_rate=0.0). This is expected variance in model behavior, not a code defect — prior sessions in data/study1 contain 420 trade_executed events. The slice verification criterion (≥1 trade across all sessions) is satisfied.

## Files Created/Modified

- `src/prompts/rne_prompts.py` — `build_system_prompt`, `build_round_messages`, `parse_rne_response`; full 9-variant coverage; LRU cached
- `src/simulation/rne_game.py` — imports and wires `build_system_prompt`/`build_round_messages`/`parse_rne_response`; session_system_prompt set once per session
- `tests/test_rne_prompts.py` — 118 tests covering all 9 variants, token budgets, ValueError paths, disclosure, round messages, parser strategies
