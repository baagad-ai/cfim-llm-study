---
id: T02
parent: S02
milestone: M001
provides:
  - src/simulation/llm_router.py — call_llm(), strip_md(), PROVIDER_KWARGS
  - mock_response cost guard returning float 0.0 (not None, not int 0)
  - DeepSeek R1 reflection override (model string + max_tokens + no response_format)
key_files:
  - src/simulation/llm_router.py
key_decisions:
  - call_llm signature uses (model_string, provider, messages, ...) so callers supply both the
    litellm model string and the PROVIDER_KWARGS lookup key explicitly — no implicit lookup from
    GameConfig inside the router; keeps the router stateless and testable in isolation
  - Gemini max_tokens enforced at 200 inside PROVIDER_KWARGS (per D022), not overridable by caller
    default; caller-supplied max_tokens applies after PROVIDER_KWARGS merge so Gemini always wins
  - time.sleep(0.5) conditioned on mock_response is None — mock calls are instant, no sleep
patterns_established:
  - cost: float = (r._hidden_params.get("response_cost") or 0.0) — always float, never None/int
  - PROVIDER_KWARGS dict keyed by provider string ("groq", "deepseek", "gemini", "mistral")
  - Reflection override pattern: copy PROVIDER_KWARGS[provider], pop "response_format", override
    model_string and max_tokens before calling litellm.completion
observability_surfaces:
  - python src/simulation/llm_router.py — standalone mock diagnostic; prints "mock cost guard: ok"
  - grep "response_cost" src/simulation/llm_router.py — shows cost guard implementation
  - call_llm propagates litellm exceptions to caller — no swallowing; callers handle retries
duration: ~20m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T02: Write llm_router.py with per-provider routing and mock guards

**Implemented `call_llm()` as the single LLM routing surface with per-provider kwargs, DeepSeek R1 reflection override, float cost guard, and a passing standalone mock self-test.**

## What Happened

Read `scripts/test_connectivity.py` and `src/simulation/config.py` first to get exact `strip_md()` and per-provider kwargs before writing anything.

Wrote `src/simulation/llm_router.py` with:
- `litellm.drop_params = True` and `litellm.set_verbose = False` at module level, after `load_dotenv`
- `strip_md()` copied verbatim (4-line function including docstring, identical to test_connectivity.py)
- `PROVIDER_KWARGS` dict with all 4 providers; Gemini includes `max_tokens: 200` per D022
- `call_llm(model_string, provider, messages, max_tokens=150, is_reflection=False, mock_response=None) -> tuple[str, float]`
  - DeepSeek reflection: overrides to `openrouter/deepseek/deepseek-r1`, `max_tokens=800`, drops `response_format` from a copy of kwargs
  - `time.sleep(0.5)` only when `mock_response is None`
  - `cost: float = (r._hidden_params.get("response_cost") or 0.0)` — float guaranteed
- `__main__` self-test: calls with `mock_response='{"action":"build"}'`, asserts `cost == 0.0` and `isinstance(cost, float)`

## Verification

```bash
# Import check
.venv/bin/python -c "from src.simulation.llm_router import call_llm, strip_md; print('import ok')"
# → import ok ✅

# Self-test (mock cost guard)
.venv/bin/python src/simulation/llm_router.py
# → mock cost guard: ok ✅

# Code review — or 0.0 present
grep "or 0\.0" src/simulation/llm_router.py
# → cost: float = (r._hidden_params.get("response_cost") or 0.0) ✅

# Code review — no bare "or 0" in executable code (docstring false-positive excluded)
grep -E "or 0[^.]" src/simulation/llm_router.py | grep -v "^\s*#"
# → only the docstring phrase "(not `or 0`)" — no actual code uses bare or 0 ✅
```

Slice-level verification: `tests/test_smoke.py` does not exist yet (T04 writes it) — expected at this stage.

## Diagnostics

```bash
# Run the standalone mock diagnostic at any time
.venv/bin/python src/simulation/llm_router.py
# Expected: "mock cost guard: ok"

# Verify DeepSeek R1 override is in code
grep "deepseek-r1" src/simulation/llm_router.py

# Verify cost guard
grep "response_cost" src/simulation/llm_router.py
```

Exceptions from `litellm.completion` propagate to the caller unchanged — GM and Agent handle retries at their level as planned.

## Deviations

None. Followed T02-PLAN exactly.

Note: The S02-PLAN task description uses a different `call_llm` signature (agent_id-based) than T02-PLAN (model_string + provider). T02-PLAN is the authoritative contract and was implemented as written. The S02-PLAN task description is a looser summary written before the detailed plan existed.

## Known Issues

None.

## Files Created/Modified

- `src/simulation/llm_router.py` — new file; `call_llm()`, `strip_md()`, `PROVIDER_KWARGS`; self-test in `__main__`
