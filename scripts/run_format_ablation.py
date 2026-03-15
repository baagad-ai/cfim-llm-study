"""Format ablation: compact vs verbose prompt — 20 calls per format per model family.

Sends 20 compact + 20 verbose act() calls per model (80 total), parses each
response with parse_agent_response(), and records parse strategy distribution.

Decision rule:
  compact parse rate ≥ 90% (≥18/20) → compact
  compact rate 85–89% (17/20)       → borderline, using verbose for safety
  compact rate < 85% (<17/20)       → verbose

Output:
  Per-model table: compact N/20 (P%), verbose N/20 (P%), DECISION
  Final summary: FORMAT DECISIONS: {family: format, ...}

Estimated wall time: ~80s (80 calls × 0.5s sleep + API latency).
Real API calls — do not run in CI.

Usage:
    python scripts/run_format_ablation.py 2>&1 | tee ablation_output.txt
"""

import sys
import time
from pathlib import Path

# Ensure project root is on sys.path when run as a script.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.simulation.llm_router import call_llm
from src.simulation.config import GameConfig, _MODEL_REGISTRY
from src.prompts.agent_action import build_act_messages, build_act_messages_verbose
from src.prompts.json_utils import parse_agent_response

# ---------------------------------------------------------------------------
# Synthetic mid-game state fixture — realistic round 12 of 25.
# ---------------------------------------------------------------------------
FIXTURE = dict(
    agent_id="a0",
    model_family="",          # filled per model below
    round_num=12,
    inventory={"wood": 2, "stone": 3, "grain": 4, "clay": 1, "fiber": 0},
    vp=6,
    buildings_built=[],
    all_agents_vp={"a0": 6, "a1": 3, "a2": 3, "a3": 2, "a4": 5, "a5": 1},
    memory=[],
)

# One representative agent per family from the phase0 config.
# phase0: a0=llama, a1=llama, a2=deepseek, a3=deepseek, a4=gemini, a5=mistral
_FAMILY_TO_AGENT = {"llama": "a0", "deepseek": "a2", "gemini": "a4", "mistral": "a5"}

CALLS_PER_FORMAT = 20
SCHEMA = {}  # parse_agent_response schema arg — unused but required by API


def _is_success(parsed: dict | None) -> bool:
    """Return True if response parsed successfully and has action_type key."""
    return parsed is not None and isinstance(parsed, dict) and "action_type" in parsed


def run_ablation_for_model(
    family: str,
    model_string: str,
    provider: str,
    buildings_config: dict,
) -> dict:
    """Send 20 compact + 20 verbose calls. Return result dict."""
    fixture = {**FIXTURE, "model_family": family, "buildings_config": buildings_config}

    compact_ok = 0
    verbose_ok = 0
    compact_failures = []
    verbose_failures = []

    print(f"\n  [{family}] compact calls ({CALLS_PER_FORMAT})...", flush=True)
    for i in range(CALLS_PER_FORMAT):
        msgs = build_act_messages(**{k: v for k, v in fixture.items() if k != "buildings_config"},
                                   buildings_config=fixture["buildings_config"])
        try:
            content, _cost = call_llm(
                model_string=model_string,
                provider=provider,
                messages=msgs,
                max_tokens=150,
            )
            parsed = parse_agent_response(content, SCHEMA)
            ok = _is_success(parsed)
            if ok:
                compact_ok += 1
            else:
                compact_failures.append(content[:120])
            print(f"    call {i+1:02d}: {'OK' if ok else 'FAIL'} — {content[:60]!r}", flush=True)
        except Exception as e:
            compact_failures.append(f"ERROR: {e}")
            print(f"    call {i+1:02d}: ERROR — {e}", flush=True)

    print(f"\n  [{family}] verbose calls ({CALLS_PER_FORMAT})...", flush=True)
    for i in range(CALLS_PER_FORMAT):
        msgs = build_act_messages_verbose(**{k: v for k, v in fixture.items() if k != "buildings_config"},
                                           buildings_config=fixture["buildings_config"])
        try:
            content, _cost = call_llm(
                model_string=model_string,
                provider=provider,
                messages=msgs,
                max_tokens=150,
            )
            parsed = parse_agent_response(content, SCHEMA)
            ok = _is_success(parsed)
            if ok:
                verbose_ok += 1
            else:
                verbose_failures.append(content[:120])
            print(f"    call {i+1:02d}: {'OK' if ok else 'FAIL'} — {content[:60]!r}", flush=True)
        except Exception as e:
            verbose_failures.append(f"ERROR: {e}")
            print(f"    call {i+1:02d}: ERROR — {e}", flush=True)

    return {
        "family": family,
        "model_string": model_string,
        "compact_ok": compact_ok,
        "verbose_ok": verbose_ok,
        "compact_failures": compact_failures,
        "verbose_failures": verbose_failures,
    }


def decide(compact_ok: int, total: int = CALLS_PER_FORMAT) -> str:
    """Apply decision rule. Returns 'compact', 'verbose', or 'verbose (borderline)'."""
    rate = compact_ok / total
    if rate >= 0.90:
        return "compact"
    elif rate >= 0.85:
        return "verbose (borderline, compact rate 85-89%)"
    else:
        return "verbose"


def main() -> None:
    print("=" * 60)
    print("FORMAT ABLATION: compact vs verbose — 20 calls per format per model")
    print(f"Total calls: {4 * 2 * CALLS_PER_FORMAT} (4 models × 2 formats × {CALLS_PER_FORMAT})")
    print("=" * 60)

    c = GameConfig.from_name("phase0")
    buildings_config = c.buildings

    results = []
    families_in_order = ["llama", "deepseek", "gemini", "mistral"]

    for family in families_in_order:
        reg = _MODEL_REGISTRY[family]
        model_string = reg["model_string"]
        # Provider = first segment of model string (e.g. "mistral", "groq", "openrouter", "gemini").
        # llm_router PROVIDER_KWARGS uses "groq" for llama (groq/llama-...).
        provider = model_string.split("/")[0]
        # Normalize openrouter/* → "openrouter" key matches PROVIDER_KWARGS entry? No.
        # PROVIDER_KWARGS keys: groq, deepseek, gemini, mistral.
        # For deepseek: model_string = "openrouter/deepseek/deepseek-chat" → provider = "openrouter"
        # but PROVIDER_KWARGS key is "deepseek". Need family name as provider key.
        # Fix: use family name directly (it matches PROVIDER_KWARGS keys for all but llama).
        # llama family → groq provider key (groq/llama-3.3-...).
        provider_key = "groq" if family == "llama" else family

        print(f"\n{'─' * 50}")
        print(f"Model family: {family} ({model_string})")
        print(f"Provider key: {provider_key}")
        t0 = time.time()
        result = run_ablation_for_model(family, model_string, provider_key, buildings_config)
        elapsed = time.time() - t0
        result["elapsed_s"] = elapsed
        results.append(result)

    # Print summary table.
    print("\n" + "=" * 60)
    print("ABLATION RESULTS")
    print("=" * 60)
    print(f"{'Family':<12} {'Compact':>10} {'Verbose':>10}  Decision")
    print("-" * 60)

    format_decisions = {}
    for r in results:
        family = r["family"]
        cn = r["compact_ok"]
        vn = r["verbose_ok"]
        cp = cn / CALLS_PER_FORMAT * 100
        vp_ = vn / CALLS_PER_FORMAT * 100
        decision = decide(cn)
        format_decisions[family] = decision.split()[0]  # "compact" or "verbose"

        row = f"{family:<12} {cn:>3}/{CALLS_PER_FORMAT} ({cp:4.0f}%)  {vn:>3}/{CALLS_PER_FORMAT} ({vp_:4.0f}%)  {decision}"
        print(row)

        if cn < 16 or vn < 16:  # < 80% on either format — likely a prompt bug
            print(f"  ⚠  WARNING: {family} <80% on at least one format — investigate prompt before T03")
        if r["compact_failures"]:
            print(f"  compact failures ({len(r['compact_failures'])}):")
            for f in r["compact_failures"][:3]:
                print(f"    {f!r}")
        if r["verbose_failures"]:
            print(f"  verbose failures ({len(r['verbose_failures'])}):")
            for f in r["verbose_failures"][:3]:
                print(f"    {f!r}")

    print("\n" + "=" * 60)
    print(f"FORMAT DECISIONS: {format_decisions}")
    print("=" * 60)

    # Print evidence for DECISIONS.md entries.
    print("\n--- DECISIONS.md evidence (paste into D041–D044) ---")
    for r in results:
        family = r["family"]
        cn = r["compact_ok"]
        vn = r["verbose_ok"]
        decision = decide(cn)
        print(
            f"| D0XX | M001/S04/T02 | prompts | Format decision: {family} | {decision} | "
            f"compact {cn}/{CALLS_PER_FORMAT}, verbose {vn}/{CALLS_PER_FORMAT}; "
            f"threshold ≥90% compact → compact, else verbose | No — post-registration lock |"
        )

    print("\nDone.")


if __name__ == "__main__":
    main()
