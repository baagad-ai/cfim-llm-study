---
id: T01
parent: S02
milestone: M001
provides:
  - src/prompts/rne_prompts.py with build_system_prompt(condition, framing) — all 9 variants cached
  - tests/test_rne_prompts.py — 42 tests covering all variants, budget, errors, determinism, content
  - RNERunner wired to call build_system_prompt once at session start and thread through all call_llm calls
key_files:
  - src/prompts/rne_prompts.py
  - src/simulation/rne_game.py
  - tests/test_rne_prompts.py
key_decisions:
  - D058: Three-part composition (framing_intro + condition_core + shared _MECHANICS). Single prompt used for both agents. Session prompt built once, threaded as system_prompt kwarg.
patterns_established:
  - build_system_prompt is @functools.lru_cache — repeated calls are free; same object returned on cache hit
  - _build_round_messages accepts optional system_prompt kwarg for injected pre-built prompt; falls back to _system_prompt() for backward compat
  - All respond call sites in run_session use session_system_prompt directly (no re-build)
observability_surfaces:
  - All 9 (condition × framing) variants verified at module import time via explicit call in test suite
  - Token estimate (len//4) verified ≤ 300 for all 9 variants (range: 241–278 tokens)
duration: ~30m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: System prompt variants — 3 conditions × 3 framings

**Added `build_system_prompt(condition, framing)` with 9 LRU-cached variants and wired it as the sole system-message source in RNERunner.**

## What Happened

Created `src/prompts/rne_prompts.py` with a three-part composition pattern:

- `_FRAMING_INTRO[framing]` — 3 framing variants (neutral/social/strategic)
- `_CONDITION_CORE[condition]` — 3 condition descriptions (A=coordination, B=mixed-motive, C=asymmetric power)
- `_MECHANICS` — shared static block (resources, values, decay rate, round count, JSON output format)

`build_system_prompt(condition, framing)` assembles them as `f"{intro}\n\n{cond_desc}\n\n{_MECHANICS}"`, validates both args against frozensets, and is decorated with `@functools.lru_cache(maxsize=None)`.

In `rne_game.py`:
- Added `from src.prompts.rne_prompts import build_system_prompt`
- Called `session_system_prompt = build_system_prompt(config.condition, config.prompt_framing)` once at session start (before `logger.log("game_start", ...)`)
- Updated `_build_round_messages` signature to accept `system_prompt: str | None = None`; when provided, uses it directly instead of calling `_system_prompt()`
- Both respond call sites (`a1_respond` and `a0_respond`) now use `session_system_prompt` instead of `_system_prompt(config, agent_id)`

Created `tests/test_rne_prompts.py` with 42 tests across 4 classes:
- `TestBuildSystemPromptAllVariants` — 18 parametrized tests (non-empty + token budget for all 9 combos)
- `TestBuildSystemPromptDeterminism` — 10 tests (determinism + cache identity)
- `TestBuildSystemPromptErrors` — 6 tests (unknown condition, framing, both, empty strings, lowercase)
- `TestBuildSystemPromptContent` — 8 content spot-checks (coordination language, defect/exploit, power, JSON, decay, framing language)

## Verification

```
pytest tests/test_rne.py tests/test_rne_prompts.py -v
# → 89 passed, 1 warning
```

Task-plan verification script:
```
A/neutral: 241 tok ok
A/social: 262 tok ok
A/strategic: 250 tok ok
B/neutral: 257 tok ok
B/social: 278 tok ok
B/strategic: 266 tok ok
C/neutral: 258 tok ok
C/social: 278 tok ok
C/strategic: 266 tok ok
```

All must-haves confirmed:
- ✅ Non-empty string for all 9 combinations (min 241 chars / 60 tokens)
- ✅ ValueError on unknown condition (`"X"`, `""`, `"a"`)
- ✅ ValueError on unknown framing (`"aggressive"`, `""`)
- ✅ Deterministic — same object returned from cache (identity test passes)
- ✅ All variants ≤ 300 tokens (range: 241–278 tok)
- ✅ RNERunner passes system prompt in messages list to call_llm (wiring confirmed via mock 3-round run)

## Diagnostics

```bash
# Inspect all 9 system prompts
python3 -c "
from src.prompts.rne_prompts import build_system_prompt
for c in ('A','B','C'):
    for f in ('neutral','social','strategic'):
        print(f'=== {c}/{f} ===')
        print(build_system_prompt(c, f))
        print()
"

# Verify cache info
python3 -c "
from src.prompts.rne_prompts import build_system_prompt
for c in ('A','B','C'):
    for f in ('neutral','social','strategic'):
        build_system_prompt(c, f)
print(build_system_prompt.cache_info())
# CacheInfo(hits=0, misses=9, maxsize=None, currsize=9)
"
```

## Deviations

None. Plan followed exactly. Note: single system prompt used for both Agent A and Agent B in a session (not two separate prompts). The placeholder `_system_prompt()` referenced "Agent A" and "Agent B" role distinctions per-agent; the new prompt drops that in favor of condition-level game mechanics description. T02 (round messages + disclosure injection) will handle per-agent role and inventory context in the user message, which is the right architectural boundary.

## Known Issues

None. The placeholder `_system_prompt()` function remains in `rne_game.py` for backward compatibility but is no longer called in any live code path during `run_session()`. T02 or T03 can remove it once the full prompt architecture is in place.
