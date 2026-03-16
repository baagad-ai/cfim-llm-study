---
id: T01
parent: S02
milestone: M001
provides:
  - build_system_prompt(condition, framing) — 9 cached system prompt variants
  - All T01 must-haves verified: non-empty, ValueError on unknown, deterministic, ≤300 tok, wired into RNERunner
key_files:
  - src/prompts/rne_prompts.py
  - src/simulation/rne_game.py
  - tests/test_rne_prompts.py
key_decisions:
  - build_system_prompt is LRU-cached with maxsize=None; called once per session at session start in RNERunner
  - Condition descriptions drawn directly from SIMULATION_DESIGN.md §3.1/§3.2; framing intros from §6.2
  - Decay rate in mechanics block is 10% (matching SIMULATION_DESIGN.md Q3 resolution)
  - Zero-quantity resources omitted from inventory string in user messages (keeps messages terse)
patterns_established:
  - System prompt is the static session prefix; user message carries per-round dynamic state
  - Disclosure injection in user message only — never system message
  - 4-strategy tolerant parser (direct → fence-strip → bracket-counter → None) handles all known LLM output variants
observability_surfaces:
  - parse_failure events logged to game.jsonl with raw[:200] for debugging
  - parse_failure_count in summary.json
duration: resumed from completed state
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: System prompt variants — 3 conditions × 3 framings

**`build_system_prompt` ships all 9 (condition × framing) cached variants; `RNERunner` calls it once per session and passes the result as system message every round.**

## What Happened

T01 was found complete on resume — `src/prompts/rne_prompts.py`, `tests/test_rne_prompts.py`, and the `rne_game.py` wiring were all already in place from earlier work. Execution focused on verifying all T01 must-haves explicitly and confirming the full test suite.

`rne_prompts.py` implements:
- `_CONDITION_CORE` dict: 3 condition descriptions (A=Pure Coordination, B=Mixed Motive, C=Asymmetric Power) drawn from SIMULATION_DESIGN.md §3.1/§3.2
- `_FRAMING_INTRO` dict: 3 framing intros (neutral/social/strategic) from §6.2
- `_MECHANICS`: shared mechanics block (decay 10%, 35 rounds, JSON-only output instruction)
- `build_system_prompt(condition, framing)`: validates inputs, assembles `intro + condition + mechanics`, caches with `@functools.lru_cache`

`rne_game.py` wiring: `build_system_prompt(config.condition, config.prompt_framing)` is called exactly once at session start (stored as `session_system_prompt`), then passed as the system message in every `call_llm` invocation for both agents and respond calls.

## Verification

T01-specific must-have verification (all pass):
```
# Must-have 1: all 9 variants return strings with 50+ chars, ≤300 tok
A/neutral: 253 tok ok  A/social: 274 tok ok  A/strategic: 262 tok ok
B/neutral: 270 tok ok  B/social: 290 tok ok  B/strategic: 278 tok ok
C/neutral: 270 tok ok  C/social: 290 tok ok  C/strategic: 278 tok ok

# Must-have 2: ValueError on unknown condition/framing
# Must-have 3: deterministic + same object from cache (a is b)
# Must-have 4: all token counts ≤ 300
# Must-have 5: RNERunner calls build_system_prompt once per session (line 355 rne_game.py)
All T01 must-haves PASS
```

Full test suite:
```
pytest tests/test_rne.py tests/test_rne_prompts.py -v
→ 165 passed, 1 warning in 1.05s
```

## Diagnostics

- `parse_failure` events in `game.jsonl` include `raw[:200]` for debugging LLM output issues
- `parse_failure_count` in `summary.json` gives aggregate failure rate per session
- `build_system_prompt` cache can be inspected: `build_system_prompt.cache_info()` → hits/misses/currsize

## Deviations

None — implementation matches the task plan exactly.

## Known Issues

None.

## Files Created/Modified

- `src/prompts/rne_prompts.py` — `build_system_prompt` + `build_round_messages` + `parse_rne_response` (complete)
- `src/simulation/rne_game.py` — wired to call `build_system_prompt` once per session; delegates to `build_round_messages`/`parse_rne_response`
- `tests/test_rne_prompts.py` — 165 tests covering all 9 prompt variants, disclosure, history, token budgets, parser strategies
