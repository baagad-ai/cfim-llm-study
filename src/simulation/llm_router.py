"""LLM routing surface for all agent and GM calls.

Two entry points:

  call_llm(family, messages, mock_response=None)
    → litellm response object
    → RNE (Study 1) engine: looks up family in PROVIDER_KWARGS, routes directly.
    → Cost guard: (r._hidden_params.get("response_cost") or 0.0)  — always float.

  call_llm_provider(model_string, provider, messages, ...)
    → (content: str, cost_usd: float)
    → Trade Island engine (agent.py, gm.py): backwards-compat interface.

Provider quirks encoded in PROVIDER_KWARGS (keyed by family name):
  - Gemini: thinking disabled (D020), no response_format (D021), max_tokens=200 (D022)
  - DeepSeek: via OpenRouter (D019), json_object mode (D017)
  - All others: json_object mode where supported

litellm.drop_params = True  is set at module level — silently drops params
the provider does not support (e.g. response_format for providers that lack it).
"""

import re
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

import litellm  # noqa: E402  (must come after env load so API keys are present)

litellm.drop_params = True   # silently drop unsupported params per provider (D020-D021)
litellm.set_verbose = False

# ---------------------------------------------------------------------------
# Per-family model strings — authoritative routing table for Study 1 (RNE).
# Keys are short family names used in RNEConfig.family_a / family_b.
# ---------------------------------------------------------------------------
_FAMILY_MODEL: dict[str, str] = {
    "llama":     "groq/llama-3.3-70b-versatile",
    "deepseek":  "openrouter/deepseek/deepseek-chat",
    "gemini":    "gemini/gemini-2.5-flash",
    "mistral":   "mistral/mistral-small-2506",
    "gpt4o-mini": "openai/gpt-4o-mini",
    "qwen":      "together_ai/Qwen/Qwen2.5-72B-Instruct-Turbo",
    "phi4":      "together_ai/microsoft/phi-4",
}

# ---------------------------------------------------------------------------
# Per-provider completion kwargs — 7 entries covering all Study 1 families.
#
# Gemini constraints (D020 / D021 / D022):
#   - thinking={'type':'disabled','budget_tokens':0}  — disables thinking mode
#   - NO response_format — json_object causes empty content on Gemini (D021)
#   - max_tokens=200 minimum — 150 leaves no headroom with partial thinking (D022)
#
# DeepSeek (D017 / D019):
#   - Routed via OpenRouter (D019)
#   - json_object mode; schema included in prompt text (D017)
#
# gpt4o-mini / qwen / phi4:
#   - json_object mode; max_tokens=150 per blueprint defaults
# ---------------------------------------------------------------------------
PROVIDER_KWARGS: dict[str, dict] = {
    "llama": {
        "response_format": {"type": "json_object"},
        "max_tokens": 150,
    },
    "deepseek": {
        "response_format": {"type": "json_object"},
        "max_tokens": 150,
    },
    "gemini": {
        "thinking": {"type": "disabled", "budget_tokens": 0},
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
        # D021 superseded by D047: with thinking=disabled, json_object mode works
        # reliably — verified 5/5 non-empty, 2 full 25-round games with 0 parse failures.
    },
    "mistral": {
        "response_format": {"type": "json_object"},
        "max_tokens": 150,
    },
    "gpt4o-mini": {
        "response_format": {"type": "json_object"},
        "max_tokens": 150,
    },
    "qwen": {
        "response_format": {"type": "json_object"},
        "max_tokens": 150,
    },
    "phi4": {
        "response_format": {"type": "json_object"},
        "max_tokens": 150,
    },
}

# ---------------------------------------------------------------------------
# Legacy provider-keyed kwargs for Trade Island engine (agent.py / gm.py).
# Keyed by provider string (e.g. "groq", "mistral") not family name.
# ---------------------------------------------------------------------------
_LEGACY_PROVIDER_KWARGS: dict[str, dict] = {
    "groq": {
        "response_format": {"type": "json_object"},
    },
    "deepseek": {
        "response_format": {"type": "json_object"},
    },
    "gemini": {
        "thinking": {"type": "disabled", "budget_tokens": 0},
        "max_tokens": 200,
        "response_format": {"type": "json_object"},
        # D047: json_object re-enabled for gemini (D021 superseded)
    },
    "mistral": {
        "response_format": {"type": "json_object"},
    },
}


def strip_md(text: str) -> str:
    """Strip markdown code fences that Gemini (and occasionally others) wrap JSON in."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


# ---------------------------------------------------------------------------
# Primary entry point — Study 1 (RNE) engine
# ---------------------------------------------------------------------------

def call_llm(
    family: str,
    messages: list,
    mock_response: str = None,
) -> object:
    """Call LiteLLM for the RNE engine and return the raw litellm response.

    Routes via PROVIDER_KWARGS keyed by family name.  Callers extract content
    and cost from the returned response object:

        r = call_llm("mistral", messages)
        content = strip_md(r.choices[0].message.content or "")
        cost = (r._hidden_params.get("response_cost") or 0.0)

    Cost guard: ``or 0.0`` (not ``or 0``) ensures the type is always float
    even when litellm returns None for mock / cached responses.

    Args:
        family:         Family key in PROVIDER_KWARGS (e.g. "mistral", "llama").
        messages:       List of {"role": ..., "content": ...} dicts.
        mock_response:  If not None, passed to litellm as mock_response — no real
                        API call, cost returns 0.0.

    Returns:
        litellm ModelResponse object.

    Raises:
        KeyError: if family is not in PROVIDER_KWARGS.
    """
    if family not in PROVIDER_KWARGS:
        raise KeyError(
            f"Unknown family {family!r}. "
            f"Known families: {sorted(PROVIDER_KWARGS)}"
        )
    if family not in _FAMILY_MODEL:
        raise KeyError(
            f"No model string registered for family {family!r}. "
            f"Known families: {sorted(_FAMILY_MODEL)}"
        )

    model_string = _FAMILY_MODEL[family]
    kwargs: dict = dict(PROVIDER_KWARGS[family])
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

    return r


# ---------------------------------------------------------------------------
# Backwards-compat entry point — Trade Island engine (agent.py / gm.py)
# ---------------------------------------------------------------------------

def call_llm_provider(
    model_string: str,
    provider: str,
    messages: list,
    max_tokens: int = 150,
    is_reflection: bool = False,
    mock_response: str = None,
) -> tuple[str, float]:
    """Call LiteLLM for the Trade Island engine and return (content, cost_usd).

    This is the legacy interface used by agent.py and gm.py.  New code should
    use call_llm() instead.

    Args:
        model_string:   Exact litellm model string, e.g. "mistral/mistral-small-2506".
        provider:       Provider key matching _LEGACY_PROVIDER_KWARGS.
        messages:       List of {"role": ..., "content": ...} dicts.
        max_tokens:     Token budget (default 150; overridden by per-provider minimum).
        is_reflection:  If True and provider=="deepseek", switches to R1 (no JSON mode).
        mock_response:  If not None, no real call is made; cost returns 0.0.

    Returns:
        (content, cost_usd) — content has markdown fences stripped; cost is float.
    """
    # DeepSeek reflection: R1 model, extended token budget, no JSON mode (D024).
    if is_reflection and provider == "deepseek":
        model_string = "openrouter/deepseek/deepseek-r1"
        max_tokens = 800
        kwargs = {
            k: v
            for k, v in _LEGACY_PROVIDER_KWARGS[provider].items()
            if k != "response_format"
        }
    else:
        kwargs = dict(_LEGACY_PROVIDER_KWARGS.get(provider, {}))

    # Per-provider max_tokens minimum takes precedence (e.g. Gemini needs 200).
    kwargs["max_tokens"] = max(max_tokens, kwargs.get("max_tokens", 0))
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
    # Test new family-based interface
    r = call_llm(
        family="mistral",
        messages=[{"role": "user", "content": "test"}],
        mock_response='{"action":"cooperate"}',
    )
    cost = (r._hidden_params.get("response_cost") or 0.0)
    assert isinstance(cost, float), f"cost must be float, got {type(cost).__name__}"
    assert cost == 0.0, f"mock cost must be 0.0, got {cost!r}"
    print("call_llm mock: ok")

    # Test legacy interface
    content, cost2 = call_llm_provider(
        model_string="mistral/mistral-small-2506",
        provider="mistral",
        messages=[{"role": "user", "content": "test"}],
        mock_response='{"action":"build"}',
    )
    assert cost2 == 0.0, f"expected cost 0.0, got {cost2!r}"
    assert isinstance(cost2, float), f"cost must be float, got {type(cost2).__name__}"
    print("call_llm_provider mock: ok")
