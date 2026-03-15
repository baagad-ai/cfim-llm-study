---
estimated_steps: 5
estimated_files: 1
---

# T02: Write llm_router.py with per-provider routing and mock guards

**Slice:** S02 — Trade Island Engine
**Milestone:** M001

## Description

Implement the single LLM routing surface that all agents and the GM call. Per-provider kwargs are copied verbatim from `test_connectivity.py` — no invention needed. The two correctness-critical items are: (1) the `mock_response` cost guard using `or 0.0` not `or 0`, and (2) the DeepSeek R1 model string override for reflection calls. Both are tested before this task is considered done.

## Steps

1. Set `litellm.drop_params = True` and `litellm.set_verbose = False` at module level in `llm_router.py`. Load `.env` at import time via `dotenv.load_dotenv`.
2. Copy `strip_md()` verbatim from `scripts/test_connectivity.py` (3-line regex function). Do not modify.
3. Define `PROVIDER_KWARGS: dict[str, dict]` mapping provider name to litellm kwargs:
   - `"groq"`: `{"response_format": {"type": "json_object"}}`
   - `"deepseek"`: `{"response_format": {"type": "json_object"}}`
   - `"gemini"`: `{"thinking": {"type": "disabled", "budget_tokens": 0}, "max_tokens": 200}`
   - `"mistral"`: `{"response_format": {"type": "json_object"}}`
   Note: Gemini `max_tokens=200` minimum per D022 — this overrides the config default for Gemini even if the config says 150.
4. Implement `call_llm(model_string: str, provider: str, messages: list, max_tokens: int = 150, is_reflection: bool = False, mock_response: str = None) -> tuple[str, float]` returning `(content, cost_usd)`:
   - If `is_reflection=True` and `provider == "deepseek"`: override `model_string = "openrouter/deepseek/deepseek-r1"`, override `max_tokens = 800`, remove `response_format` from kwargs (R1 has no JSON mode).
   - Build kwargs from `PROVIDER_KWARGS[provider]`, merge with `{"max_tokens": max_tokens, "num_retries": 3}`.
   - If `mock_response` is not None, pass as `mock_response=mock_response` kwarg to `litellm.completion`.
   - Add `time.sleep(0.5)` after each real call (omit for mock calls — check `mock_response is not None`).
   - Extract cost: `cost = (r._hidden_params.get("response_cost") or 0.0)` — literal `or 0.0`, not `or 0`.
   - Return `(strip_md(r.choices[0].message.content or ""), cost)`.
5. Write a self-test block (`if __name__ == "__main__"`) that: calls `call_llm` with `mock_response='{"action":"build"}'`, asserts returned cost is `0.0` (not `None` and not `0`), prints `"mock cost guard: ok"`. Run it: `python src/simulation/llm_router.py`.

## Must-Haves

- [ ] `litellm.drop_params = True` set at module level before any other litellm usage
- [ ] `strip_md()` copied verbatim — identical to `test_connectivity.py` version
- [ ] Cost extracted with `or 0.0` — confirmed in code, not just `or 0`
- [ ] DeepSeek reflection: model string switches to `openrouter/deepseek/deepseek-r1`, `max_tokens=800`, no `response_format`
- [ ] `time.sleep(0.5)` present for real calls, skipped for mock calls
- [ ] Mock cost guard self-test passes

## Verification

- `python -c "from src.simulation.llm_router import call_llm, strip_md; print('import ok')"` exits 0
- `python src/simulation/llm_router.py` prints `"mock cost guard: ok"`
- Code review: grep `or 0.0` present in `llm_router.py`; grep `or 0[^.]` absent (would catch `or 0` without decimal)

## Observability Impact

- Signals added/changed: every `call_llm` returns `(content, cost_usd)` — callers accumulate cost; no internal logging here (callers log via `GameLogger`)
- How a future agent inspects this: `grep "response_cost" src/simulation/llm_router.py` shows the guard; mock test in `__main__` is runnable as a standalone diagnostic
- Failure state exposed: on `litellm.completion` exception, the exception propagates to the caller — GM and Agent handle retries at their level

## Inputs

- `scripts/test_connectivity.py` — source of `strip_md()` and per-provider kwargs to copy verbatim
- `config/litellm_config.yaml` — reference for model strings and `max_tokens` defaults
- `src/simulation/config.py` — `PROVIDER_KWARGS` keys must align with `agent_models[].provider` field values from T01

## Expected Output

- `src/simulation/llm_router.py` — `call_llm()`, `strip_md()`, `PROVIDER_KWARGS`; self-test passes
