---
id: T01
parent: S01
milestone: M001
provides:
  - RNEConfig Pydantic model with all Study 1 fields and defaults
  - GameConfig.from_rne() factory for 2-agent bilateral game config
  - GameLogger line-buffered JSONL writer (existing, verified)
  - call_llm(family, messages, mock_response) returning litellm response
  - PROVIDER_KWARGS with 7 family entries (llama, deepseek, gemini, mistral, gpt4o-mini, qwen, phi4)
  - strip_md utility
  - call_llm_provider (backward-compat for Trade Island engine)
  - tests/test_rne.py with 25 passing T01 tests + 5 skipped stubs for T02+
key_files:
  - src/simulation/config.py
  - src/simulation/logger.py
  - src/simulation/llm_router.py
  - src/simulation/__init__.py
  - tests/test_rne.py
  - .gsd/milestones/M001/slices/S01/S01-PLAN.md
  - .gsd/milestones/M001/slices/S01/tasks/T01-PLAN.md
key_decisions:
  - D041 — call_llm split into two entry points (RNE vs Trade Island)
  - D042 — RNEConfig disclosure/prompt_framing have defaults (blind/neutral)
patterns_established:
  - family-keyed PROVIDER_KWARGS pattern (7 providers, family name as key)
  - call_llm returns raw litellm response; callers extract content + cost
  - call_llm_provider alias pattern in agent.py/gm.py (import as call_llm for drop-in)
observability_surfaces:
  - GameLogger uses buffering=1 — every log() call immediately readable on disk
  - call_llm mock_response=... returns cost=0.0 float; verifiable with r._hidden_params
  - litellm.drop_params=True suppresses provider-unsupported kwarg errors silently
duration: ~45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Config, Logger, and LLM Router

**Added `RNEConfig` + 7-family `PROVIDER_KWARGS` + family-keyed `call_llm` to the simulation package; all 3 task verification checks pass; 48 tests green.**

## What Happened

The simulation package already existed from prior slices (S02/S03 Trade Island engine). This task added the Study 1 (RNE) surface alongside without breaking the existing engine.

**config.py:** Added `RNEConfig` Pydantic BaseModel with the 9 Study 1 fields. `disclosure` and `prompt_framing` have defaults (`"blind"`, `"neutral"`) matching the control conditions — the task plan verification command omits them so defaults were required. Added `GameConfig.from_rne()` factory that builds a 2-agent bilateral `GameConfig` from an `RNEConfig`.

**logger.py:** Already correct — `GameLogger('id', path)` constructor, `buffering=1`, `log(event, **fields)` writing `{ts, event, game_id, **fields}`. No changes needed.

**llm_router.py:** Rewrote to add the RNE-facing surface while preserving the Trade Island engine. The old `call_llm(model_string, provider, messages, ...)→(content, cost)` was renamed to `call_llm_provider` (backward-compat). The new `call_llm(family, messages, mock_response)→litellm_response` routes via a 7-family `PROVIDER_KWARGS` dict. `litellm.drop_params = True` remains at module level. A `_FAMILY_MODEL` dict maps family names to exact litellm model strings.

`agent.py` and `gm.py` updated to `from src.simulation.llm_router import call_llm_provider as call_llm` — drop-in rename, no functional change. `game.py` cost-tracking patch updated to patch `call_llm_provider` instead of `call_llm`.

`json_utils.py` lazy import of `PROVIDER_KWARGS` works unchanged since keys are family names in both old and new dicts.

**tests/test_rne.py:** Created 30 test cases — 25 passing (T01 coverage for RNEConfig, GameLogger, PROVIDER_KWARGS, call_llm) + 5 skipped stubs for T02 engine and T03 metrics.

## Verification

All three task plan verification commands pass:
```
config ok     ← RNEConfig(family_a='mistral', family_b='llama', condition='A') with rounds=35, decay_rate=0.10, len(session_id)==8
logger ok     ← GameLogger writes round_end line; d['event']=='round_end'; d['round']==1
router ok     ← 'gemini' in PROVIDER_KWARGS; no 'response_format'; 'thinking' present
```

Full test suite: `pytest tests/` — **48 passed, 5 skipped** (0 failures). The 5 skips are T02+/T03+ stubs in test_rne.py.

Must-have checklist:
- ✅ `RNEConfig` has all 9 fields with correct types/defaults
- ✅ `GameLogger.log()` writes line-buffered JSONL with ISO8601 ts
- ✅ `call_llm(family, messages, mock_response=None)` returns litellm response
- ✅ `litellm.drop_params = True` at module level
- ✅ All 7 provider entries in `PROVIDER_KWARGS` with correct kwargs

## Diagnostics

```bash
# Verify PROVIDER_KWARGS structure
python -c "from src.simulation.llm_router import PROVIDER_KWARGS; print(list(PROVIDER_KWARGS))"
# → ['llama', 'deepseek', 'gemini', 'mistral', 'gpt4o-mini', 'qwen', 'phi4']

# Mock call cost guard
python -c "
from src.simulation.llm_router import call_llm
r = call_llm('mistral', [{'role':'user','content':'x'}], mock_response='{\"a\":1}')
print(type(r._hidden_params.get('response_cost') or 0.0))
"
# → <class 'float'>

# GameLogger line buffering
python -c "from src.simulation.logger import GameLogger; import tempfile,pathlib; t=tempfile.mkdtemp(); l=GameLogger('x',pathlib.Path(t)); print(l._file.line_buffering)"
# → True
```

## Deviations

1. **`disclosure` and `prompt_framing` given defaults** (blind/neutral): Task plan verification command calls `RNEConfig(family_a='mistral', family_b='llama', condition='A')` without these fields. Added defaults matching control conditions so the verification command works. Fields are still validated against their Literal types when provided.

2. **`call_llm_provider` instead of replacing `call_llm`**: Trade Island engine has 23 call sites using the old `(model_string, provider, messages)→(content, cost)` signature. Renamed old function to `call_llm_provider`; updated agent.py, gm.py, game.py imports. New `call_llm(family, messages)→response` is the RNE surface. Decision recorded as D041.

## Known Issues

None. All verification checks pass. Trade Island engine unaffected (48/48 tests green).

## Files Created/Modified

- `src/simulation/config.py` — added `RNEConfig`, `GameConfig.from_rne()`; added `uuid`, `Literal` imports
- `src/simulation/llm_router.py` — rewrote: new `call_llm(family, ...)`, 7-family `PROVIDER_KWARGS`, `_FAMILY_MODEL`, `call_llm_provider` (legacy), `_LEGACY_PROVIDER_KWARGS`
- `src/simulation/__init__.py` — exports `RNEConfig` alongside existing exports
- `src/simulation/agent.py` — `import call_llm_provider as call_llm`
- `src/simulation/gm.py` — `import call_llm_provider as call_llm`
- `src/simulation/game.py` — patches `call_llm_provider` (not `call_llm`) for cost tracking
- `tests/test_rne.py` — new; 30 test cases (25 passing T01, 5 skipped T02+/T03+)
- `.gsd/milestones/M001/slices/S01/S01-PLAN.md` — new; slice plan
- `.gsd/milestones/M001/slices/S01/tasks/T01-PLAN.md` — new; task plan
- `.gsd/DECISIONS.md` — appended D041, D042
