#!/usr/bin/env python3
"""
Test LiteLLM connectivity to all 4 providers.
Verifies: JSON mode, thinking disabled (Gemini), cost tracking, basic response.

Run: python scripts/test_connectivity.py
Expected: 4 green checks, total cost ~$0.0001
"""

import os
import json
import re
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

try:
    import litellm
    litellm.set_verbose = False
    litellm.drop_params = True  # silently drop unsupported params per provider
except ImportError:
    print("❌ litellm not installed. Run: pip install litellm")
    sys.exit(1)

MODELS = [
    {
        "label":   "Groq / Llama 3.3 70B",
        "model":   "groq/llama-3.3-70b-versatile",
        "key_env": "GROQ_API_KEY",
        "kwargs":  {"response_format": {"type": "json_object"}},
        "notes":   "Automatic prompt caching (50% discount on cached input tokens)",
    },
    {
        "label":   "OpenRouter / DeepSeek V3",
        "model":   "openrouter/deepseek/deepseek-chat",
        "key_env": "OPENROUTER_API_KEY",
        "kwargs":  {"response_format": {"type": "json_object"}},
        "notes":   "Direct DeepSeek API unavailable from India — OpenRouter proxy",
    },
    {
        "label":   "Gemini 2.5 Flash (paid tier)",
        "model":   "gemini/gemini-2.5-flash",
        "key_env": "GOOGLE_API_KEY",
        "kwargs":  {"thinking": {"type": "disabled", "budget_tokens": 0}},
        "notes":   "thinking disabled → reasoning_tokens=None. Requires paid GCP billing key.",
    },
    {
        "label":   "Mistral Small 2506",
        "model":   "mistral/mistral-small-2506",
        "key_env": "MISTRAL_API_KEY",
        "kwargs":  {"response_format": {"type": "json_object"}},
        "notes":   "Pinned to 2506 dated version (3.1-2503 no longer available)",
    },
]


def strip_md(text: str) -> str:
    """Strip markdown code fences that Gemini sometimes wraps JSON in."""
    text = text.strip()
    text = re.sub(r"^```json\s*", "", text)
    text = re.sub(r"^```\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def test_model(cfg: dict) -> dict:
    api_key = os.environ.get(cfg["key_env"])
    if not api_key:
        return {"label": cfg["label"], "status": "❌ MISSING KEY",
                "error": f"{cfg['key_env']} not set in .env", "cost_usd": 0}
    try:
        r = litellm.completion(
            model=cfg["model"],
            api_key=api_key,
            messages=[{"role": "user",
                       "content": 'Output JSON only: {"status":"ok","provider":"test"}'}],
            max_tokens=200,
            **cfg["kwargs"],
        )
        raw = r.choices[0].message.content or ""
        parsed = json.loads(strip_md(raw))
        json_ok = parsed.get("status") == "ok"

        # Gemini-specific: verify thinking is actually off
        reasoning_tokens = None
        if hasattr(r.usage, "completion_tokens_details"):
            reasoning_tokens = getattr(r.usage.completion_tokens_details, "reasoning_tokens", None)

        cost = getattr(r, "_hidden_params", {}).get("response_cost", 0) or 0

        status = "✅ OK" if json_ok else "⚠️  JSON parse failed"
        if "gemini" in cfg["model"] and reasoning_tokens is not None:
            status += " ⚠️  thinking NOT disabled!"

        return {
            "label": cfg["label"],
            "status": status,
            "json_valid": json_ok,
            "input_tokens": r.usage.prompt_tokens,
            "output_tokens": r.usage.completion_tokens,
            "reasoning_tokens": reasoning_tokens,
            "cost_usd": round(cost, 7),
        }

    except Exception as e:
        return {"label": cfg["label"], "status": "❌ ERROR",
                "error": str(e)[:250], "cost_usd": 0}


def main():
    print("\n🔬 Pairwise Behavioral Signatures — Provider Connectivity Test")
    print("=" * 60)

    total_cost = 0.0
    results = []

    for cfg in MODELS:
        print(f"\n{cfg['label']}")
        print(f"  model: {cfg['model']}")
        result = test_model(cfg)
        results.append(result)
        time.sleep(0.5)

        print(f"  {result['status']}")
        if "error" in result:
            print(f"  error: {result['error']}")
        else:
            print(f"  tokens: {result['input_tokens']} in / {result['output_tokens']} out")
            if result.get("reasoning_tokens") is not None:
                print(f"  reasoning_tokens: {result['reasoning_tokens']} ← should be None")
            else:
                if "gemini" in cfg["model"]:
                    print(f"  reasoning_tokens: None ✅ thinking disabled")
            print(f"  cost: ${result['cost_usd']:.7f}")
            total_cost += result["cost_usd"]
        print(f"  note: {cfg['notes']}")

    print("\n" + "=" * 60)
    ok_count = sum(1 for r in results if "✅" in r["status"])
    print(f"Result: {ok_count}/4 providers connected")
    print(f"Total cost: ${total_cost:.6f}")

    if ok_count == 4:
        print("\n✅ ALL SYSTEMS GO — proceed to M001/S02 (Concordia integration)")
    else:
        failed = [r["label"] for r in results if "✅" not in r["status"]]
        print(f"\n⚠️  Blocked providers: {', '.join(failed)}")
        print("   Fix .env keys before proceeding.")

    return 0 if ok_count == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
