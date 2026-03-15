---
id: T04
parent: S03
milestone: M001
provides:
  - tests/test_prompts.py — 18 tests covering parser edge cases, token budgets, config shapes, kwarg inspection
key_files:
  - tests/test_prompts.py
key_decisions: []
patterns_established:
  - Test classes group by functional concern (parse strategies, formatting, token budgets, config shapes, provider kwargs)
  - Token budget tests use chars//4 <= N (tolerant upper bound), not exact match
  - test_truncated_json_returns_none asserts `result is None` (not just falsy) — the sentinel distinction matters for caller code
observability_surfaces:
  - none
duration: 15m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T04: Write tests/test_prompts.py covering all parser cases and token budgets

**18 tests written and passing — all 5 parse strategies, token budgets, phase0 config shape, mono configs, and provider kwargs verified.**

## What Happened

Inspected `src/prompts/json_utils.py`, `agent_action.py`, `trade_response.py`, `src/simulation/config.py`, and `src/simulation/llm_router.PROVIDER_KWARGS` before writing any tests. Confirmed token budgets (act=83, respond=66) and PROVIDER_KWARGS structure (gemini: no response_format; mistral/groq/deepseek: has response_format keyed under their family or provider name).

Wrote `tests/test_prompts.py` with 6 test classes as specified:

- **TestParseAgentResponse** (5 tests): valid JSON, fenced JSON (markdown fence stripped by strip_md), JSON embedded in prose (bracket-counter extraction), truncated JSON (returns exactly None), DeepSeek think-prefix (strip_think then parse).
- **TestFormatInventory** (2 tests): typical inventory → `W2 S3 G4 C1 F0`, all-zeros not omitted.
- **TestTokenBudgets** (2 tests): act ≤ 108 tok (actual: 83), respond ≤ 72 tok (actual: 66).
- **TestPhase0Config** (3 tests): 6 agents, all 4 families present, exact counts (2/2/1/1).
- **TestMonoConfigs** (3 tests): llama-mono, deepseek-mono, gemini-mono each 6 agents all-same-family.
- **TestGetCompletionKwargs** (3 tests): gemini has no response_format, mistral has response_format, returns a copy (mutation doesn't leak back).

Note: `get_completion_kwargs` uses PROVIDER_KWARGS which is keyed by provider-level strings — 'mistral' maps correctly because PROVIDER_KWARGS has a 'mistral' key.

## Verification

```
pytest tests/test_prompts.py -v   → 18 passed
pytest tests/ -v                  → 23 passed (18 + 5 smoke, no regressions)
python -c "...phase0 ok"          → phase0 ok
```

All slice verification checks pass.

## Diagnostics

```bash
# Spot-check parser directly
python -c "from src.prompts.json_utils import parse_agent_response; print(parse_agent_response('<think>r</think>\n{\"action_type\":\"hoard\"}', {}))"

# Token budget introspection
python -c "
from src.prompts.agent_action import build_act_messages
from src.simulation.config import _STANDARD_BUILDINGS
msgs = build_act_messages('a0','mistral',8,{'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0},6,[],{'a0':6,'a1':3},[],_STANDARD_BUILDINGS)
print('act_tok:', sum(len(m['content']) for m in msgs)//4)
"
```

## Deviations

None. All test cases and assertions match the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `tests/test_prompts.py` — created; 18 tests across 6 classes covering all S03 acceptance criteria
- `.gsd/milestones/M001/slices/S03/S03-PLAN.md` — T04 marked `[x]`
