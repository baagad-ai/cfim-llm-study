#!/usr/bin/env python3
"""
Test LiteLLM connectivity to all 4 providers.
Verifies: JSON mode, cost tracking, basic response.
Run: python scripts/test_connectivity.py
"""

import os
import json
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
project_root = Path(__file__).parent.parent
load_dotenv(project_root / ".env")

try:
    import litellm
    litellm.set_verbose = False
    litellm.drop_params = True  # Ignore unsupported params per provider
except ImportError:
    print("❌ litellm not installed. Run: pip install litellm")
    sys.exit(1)

# Test prompt: minimal, forces JSON output
TEST_PROMPT = """Output JSON only: {"status": "ok", "model": "your_model_name"}"""

MODELS = {
    "llama-70b": {
        "model": "groq/llama-3.3-70b-versatile",
        "api_key_env": "GROQ_API_KEY",
        "extra_kwargs": {"response_format": {"type": "json_object"}},
    },
    "deepseek-chat": {
        "model": "deepseek/deepseek-chat",
        "api_key_env": "DEEPSEEK_API_KEY",
        "extra_kwargs": {"response_format": {"type": "json_object"}},
    },
    "gemini-flash": {
        "model": "gemini/gemini-2.5-flash",
        "api_key_env": "GOOGLE_API_KEY",
        "extra_kwargs": {
            "response_format": {"type": "json_object"},
            # CRITICAL: disable thinking mode to prevent 5-12× token inflation
            "thinking": {"type": "disabled"},
        },
    },
    "mistral-small": {
        "model": "mistral/mistral-small-3.1-2503",
        "api_key_env": "MISTRAL_API_KEY",
        "extra_kwargs": {"response_format": {"type": "json_object"}},
    },
}


def test_model(name: str, config: dict) -> dict:
    """Test a single model. Returns result dict."""
    api_key = os.environ.get(config["api_key_env"])
    if not api_key:
        return {
            "model": name,
            "status": "❌ MISSING KEY",
            "error": f"{config['api_key_env']} not set in .env",
            "cost_usd": 0,
        }

    try:
        response = litellm.completion(
            model=config["model"],
            messages=[{"role": "user", "content": TEST_PROMPT}],
            api_key=api_key,
            max_tokens=50,
            **config.get("extra_kwargs", {}),
        )

        content = response.choices[0].message.content.strip()

        # Try to parse JSON
        try:
            parsed = json.loads(content)
            json_ok = parsed.get("status") == "ok"
        except json.JSONDecodeError:
            json_ok = False

        cost = getattr(response, "_hidden_params", {}).get("response_cost", 0) or 0

        return {
            "model": name,
            "status": "✅ OK" if json_ok else "⚠️  JSON FAIL",
            "json_valid": json_ok,
            "response_preview": content[:80],
            "cost_usd": round(cost, 6),
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
        }

    except Exception as e:
        return {
            "model": name,
            "status": "❌ ERROR",
            "error": str(e)[:200],
            "cost_usd": 0,
        }


def main():
    print("\n🔬 Pairwise Behavioral Signatures — Provider Connectivity Test")
    print("=" * 60)

    total_cost = 0.0
    results = []

    for name, config in MODELS.items():
        print(f"\nTesting {name}...", end=" ", flush=True)
        result = test_model(name, config)
        results.append(result)

        print(result["status"])
        if "error" in result:
            print(f"   Error: {result['error']}")
        elif "response_preview" in result:
            print(f"   Response: {result['response_preview']}")
            print(f"   Tokens: {result['input_tokens']} in / {result['output_tokens']} out")
            print(f"   Cost: ${result['cost_usd']:.6f}")
            total_cost += result["cost_usd"]

    print("\n" + "=" * 60)
    print(f"Total cost: ${total_cost:.6f}")

    # Summary
    ok_count = sum(1 for r in results if "✅" in r["status"])
    print(f"\nResult: {ok_count}/4 providers connected")

    if ok_count == 4:
        print("✅ All providers ready. Proceed to S01/T02: run simulation setup.")
    elif ok_count > 0:
        print("⚠️  Some providers missing. Add missing keys to .env before Phase 0.")
    else:
        print("❌ No providers connected. Check .env file.")

    return 0 if ok_count == 4 else 1


if __name__ == "__main__":
    sys.exit(main())
