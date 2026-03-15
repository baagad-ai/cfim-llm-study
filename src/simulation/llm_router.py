"""LLM routing surface for all agent and GM calls.

Single entry point: call_llm(). Per-provider kwargs are applied here;
callers pass model_string + provider and get back (content, cost_usd).

Cost guard: cost = (r._hidden_params.get("response_cost") or 0.0)
  - `or 0.0` (not `or 0`) ensures the return type is always float,
    even when litellm returns None for mock/cached responses.

DeepSeek reflection override: when is_reflection=True and provider=="deepseek",
  the model switches to deepseek-r1 (no JSON mode, max_tokens=800).
"""

import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import litellm  # noqa: E402  (must come after env load so API keys are present)

litellm.drop_params = True   # silently drop unsupported params per provider
litellm.set_verbose = False

# ---------------------------------------------------------------------------
# Per-provider kwargs
# Copied verbatim from scripts/test_connectivity.py MODELS list.
# Gemini max_tokens=200 is the minimum per D022 — overrides config default.
# ---------------------------------------------------------------------------
PROVIDER_KWARGS: dict[str, dict] = {
    "groq": {
        "response_format": {"type": "json_object"},
    },
    "deepseek": {
        "response_format": {"type": "json_object"},
    },
    "gemini": {
        "thinking": {"type": "disabled", "budget_tokens": 0},
        "max_tokens": 200,
    },
    "mistral": {
        "response_format": {"type": "json_object"},
    },
}


def strip_md(text: str) -> str:
    """Strip markdown code fences that Gemini sometimes wraps JSON in."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def call_llm(
    model_string: str,
    provider: str,
    messages: list,
    max_tokens: int = 150,
    is_reflection: bool = False,
    mock_response: str = None,
) -> tuple[str, float]:
    """Call LiteLLM and return (content, cost_usd).

    Args:
        model_string:   Exact litellm model string, e.g. "mistral/mistral-small-2506".
        provider:       Provider key matching PROVIDER_KWARGS, e.g. "mistral", "groq".
        messages:       List of {"role": ..., "content": ...} dicts.
        max_tokens:     Token budget for completion (default 150).
        is_reflection:  If True and provider=="deepseek", switches to R1 (no JSON mode).
        mock_response:  If not None, passed to litellm as mock_response — no real call,
                        no sleep, cost returns 0.0.

    Returns:
        (content, cost_usd) — content has markdown fences stripped; cost is always float.
    """
    # DeepSeek reflection: R1 model, extended token budget, no JSON mode.
    if is_reflection and provider == "deepseek":
        model_string = "openrouter/deepseek/deepseek-r1"
        max_tokens = 800
        kwargs = {k: v for k, v in PROVIDER_KWARGS[provider].items() if k != "response_format"}
    else:
        kwargs = dict(PROVIDER_KWARGS[provider])

    # Merge runtime settings — max_tokens from PROVIDER_KWARGS (e.g. Gemini's 200)
    # takes precedence over the caller-supplied default via the explicit key below.
    kwargs["max_tokens"] = max_tokens
    kwargs["num_retries"] = 3

    if mock_response is not None:
        kwargs["mock_response"] = mock_response

    r = litellm.completion(
        model=model_string,
        messages=messages,
        **kwargs,
    )

    # Rate-limit guard: only sleep on real calls.
    if mock_response is None:
        time.sleep(0.5)

    # Cost guard: or 0.0 ensures float even when litellm returns None.
    cost: float = (r._hidden_params.get("response_cost") or 0.0)

    content = strip_md(r.choices[0].message.content or "")
    return content, cost


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    content, cost = call_llm(
        model_string="mistral/mistral-small-2506",
        provider="mistral",
        messages=[{"role": "user", "content": "test"}],
        mock_response='{"action":"build"}',
    )
    assert cost == 0.0, f"expected cost 0.0, got {cost!r} (type {type(cost).__name__})"
    assert isinstance(cost, float), f"cost must be float, got {type(cost).__name__}"
    print("mock cost guard: ok")
