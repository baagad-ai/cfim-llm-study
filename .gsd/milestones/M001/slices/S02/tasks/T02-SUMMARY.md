---
id: T02
parent: S02
milestone: M001
provides:
  - src/prompts/rne_prompts.py with build_round_messages(config, round_num, agent_id, inventory, history, opponent_family=None)
  - tests/test_rne_prompts.py — 96 tests total (42 from T01 + 54 new covering structure, disclosure, history, token budget)
  - src/simulation/rne_game.py — _build_round_messages delegates to public build_round_messages; build_round_messages imported
key_files:
  - src/prompts/rne_prompts.py
  - src/simulation/rne_game.py
  - tests/test_rne_prompts.py
key_decisions:
  - Disclosure injected into user message only (not system). System stays static/cached; per-round identity signal goes in user where it belongs.
  - _build_round_messages in rne_game.py kept as thin wrapper (signature compat) delegating to public fn. system_prompt kwarg accepted but ignored — build_system_prompt is LRU-cached so calling it every round is free.
  - Zero-quantity resources omitted from inventory string to keep user message concise.
patterns_established:
  - build_round_messages is the canonical per-round message builder; call sites in rne_game.py use it via the wrapper
  - Disclosure: config.disclosure drives the injection decision; opponent_family=None is safe in both modes (no injection when None)
  - History: last ≤3 items from history list; caller maintains the list
observability_surfaces:
  - Token budget verified across all 18 combos (3 conditions × 3 framings × 2 disclosure): range 266–311 tok, max 311 (budget 400)
  - Parametrized tests cover all disclosure × condition × framing combos — leaks caught automatically
duration: ~25m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Round messages + disclosure injection

**Added `build_round_messages(...)` to `rne_prompts.py` with correct disclosure injection and history truncation; wired into `rne_game.py`.**

## What Happened

Added `build_round_messages(config, round_num, agent_id, inventory, history, opponent_family=None)` to `src/prompts/rne_prompts.py`.

Implementation:
- Calls `build_system_prompt(config.condition, config.prompt_framing)` for the system message — LRU-cached, free to call each round.
- User message assembles: round number/total, non-zero inventory resources, last ≤3 history entries.
- When `config.disclosure == "disclosed"` and `opponent_family` is not None: appends `"Your opponent is a {opponent_family} model."` to the user message only. System message is never modified.
- Zero-quantity resources are filtered from the inventory string; empty inventory renders as `"empty"`.

In `src/simulation/rne_game.py`:
- Added `build_round_messages` to the import from `src.prompts.rne_prompts`.
- Replaced `_build_round_messages` body with a thin delegation call to the public function. The `system_prompt` kwarg is kept for signature compatibility but ignored (the cached function is free to call).

Added 54 new tests in `tests/test_rne_prompts.py` across 4 classes:
- `TestBuildRoundMessagesStructure` — 9 tests (list structure, roles, round/inventory content, zero-resource filtering, system content identity)
- `TestBuildRoundMessagesDisclosure` — 15 parametrized + standalone tests (blind no-leak for all 9 condition×framing combos, disclosed injection for all 9, user-only placement, None-safety)
- `TestBuildRoundMessagesHistory` — 5 tests (no history, last-3 present, earlier excluded, single entry, exactly-3 entries)
- `TestBuildRoundMessagesTokenBudget` — 18 parametrized tests (all condition × framing × disclosure combos ≤ 400 tokens)

## Verification

```
pytest tests/test_rne.py tests/test_rne_prompts.py -v
# → 143 passed, 1 warning
```

Task-plan disclosure verification script:
```
disclosure injection ok
```

Token budget across all 18 combos:
```
A/neutral/blind: 266 tok  A/neutral/disclosed: 274 tok
A/social/blind:  287 tok  A/social/disclosed:  295 tok
A/strategic/blind: 275 tok  A/strategic/disclosed: 283 tok
B/neutral/blind: 283 tok  B/neutral/disclosed: 291 tok
B/social/blind:  303 tok  B/social/disclosed:  311 tok
B/strategic/blind: 291 tok  B/strategic/disclosed: 299 tok
C/neutral/blind: 283 tok  C/neutral/disclosed: 291 tok
C/social/blind:  303 tok  C/social/disclosed:  311 tok
C/strategic/blind: 291 tok  C/strategic/disclosed: 299 tok
max: 311 (budget: 400)
```

All must-haves confirmed:
- ✅ Returns list[dict] with system + user message for every combination
- ✅ Blind: opponent family name NOT present in any message content (18 parametrized tests)
- ✅ Disclosed: opponent family name present in user message content (18 parametrized tests)
- ✅ Disclosed injection in user message only — not system (explicit test)
- ✅ History injection: last ≤3 rounds included; older rounds excluded (5 tests)
- ✅ Token count ≤ 400 for all 18 combinations (range 266–311)

## Diagnostics

```bash
# Inspect round messages for both disclosure modes
python3 -c "
from src.simulation.config import RNEConfig
from src.prompts.rne_prompts import build_round_messages

cfg_blind = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='blind', prompt_framing='neutral')
cfg_disc  = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='disclosed', prompt_framing='neutral')

blind = build_round_messages(cfg_blind, 5, 'a0', {'W':3,'S':2}, ['r1: traded','r2: no trade','r3: traded'], 'llama')
disc  = build_round_messages(cfg_disc,  5, 'a0', {'W':3,'S':2}, ['r1: traded','r2: no trade','r3: traded'], 'llama')

print('=== BLIND user msg ===')
print(blind[1]['content'])
print()
print('=== DISCLOSED user msg ===')
print(disc[1]['content'])
"
```

## Deviations

One minor deviation: the existing `_build_round_messages` in `rne_game.py` previously injected the disclosure info into the **system** message. The task plan (step 4) and must-have clearly specify injection into the **user** message. The new public function correctly puts it in the user message; the wrapper drops the old system-injection logic. This is a spec-alignment fix, not a feature change.

The `system_prompt` kwarg on `_build_round_messages` is retained for signature compat but is now a no-op — callers passing it will not cause errors. T03 can remove the wrapper entirely once all call sites have been verified.

## Known Issues

None. The old `_system_prompt()` function in `rne_game.py` is still present but no longer called (flagged in T01 summary). Safe to remove in T03 cleanup.

## Slice-Level Verification Status (intermediate)

```
pytest tests/test_rne.py tests/test_rne_prompts.py -v → 143 passed ✅
run_rne.py smoke run → pending (T03) ❌
trade_executed count ≥1 → pending (T03) ❌
cost ≤ $0.05 → pending (T03) ❌
```

## Files Created/Modified

- `src/prompts/rne_prompts.py` — added `build_round_messages` public function + updated module docstring + TYPE_CHECKING import
- `src/simulation/rne_game.py` — imported `build_round_messages`; replaced `_build_round_messages` body with delegation wrapper
- `tests/test_rne_prompts.py` — added 54 new tests across 4 classes; updated module docstring and imports
