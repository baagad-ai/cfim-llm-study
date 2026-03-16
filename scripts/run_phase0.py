#!/usr/bin/env python
"""run_phase0.py — Phase 0 Calibration runner for Study 1.

Runs 4 monoculture families × 10 replicate sessions × 3 conditions ×
2 disclosure variants = 240 RNE sessions total.

Each session is one family playing against itself so we measure per-family
parse reliability, trade acceptance rate, and baseline cooperation metrics
before collecting full CFIM pairwise data in M002.

Session output lands in ``data/phase0/sessions/{session_id}/``
(summary.json + game.jsonl + metadata.json), matching the layout expected
by the S03 verification checks.

Usage::

    # Full 240-session run:
    python scripts/run_phase0.py

    # 4-session smoke (1 per family, condition A, blind):
    python scripts/run_phase0.py --smoke

    # Resume from last completed session (skips already-written summaries):
    python scripts/run_phase0.py --resume

    # Dry-run with mock responses (zero cost, no API calls):
    python scripts/run_phase0.py --mock

    # Run a specific family only (useful for re-running a failed family):
    python scripts/run_phase0.py --family llama

Options
-------
--smoke       Run 4 sessions only (1 per family, condition A, blind) for routing verification.
--resume      Skip sessions whose summary.json already exists in data/phase0/sessions/.
--mock        Use mock LLM responses (zero cost). For CI / dry-run only.
--family      Restrict run to one family (llama|deepseek|gemini|mistral).
--data-dir    Override output root (default: data/phase0/sessions).
--concurrency Not yet implemented — sessions run sequentially.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from itertools import product
from pathlib import Path
from typing import Literal

# Ensure src/ is importable when run from project root without editable install.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.simulation.config import RNEConfig   # noqa: E402
from src.simulation.rne_game import RNERunner  # noqa: E402

# ---------------------------------------------------------------------------
# Phase 0 parameters — locked by S03 plan (do not change post-OSF)
# ---------------------------------------------------------------------------

#: Four CFIM families run as monoculture (family_a == family_b).
PHASE0_FAMILIES: list[str] = ["llama", "deepseek", "gemini", "mistral"]

#: Three experimental conditions (§3.1).
CONDITIONS: list[Literal["A", "B", "C"]] = ["A", "B", "C"]

#: Two disclosure variants (§3.3).
DISCLOSURES: list[Literal["blind", "disclosed"]] = ["blind", "disclosed"]

#: Replicates per (family, condition, disclosure) cell.
REPLICATES: int = 10

#: Prompt framing: neutral for all Phase 0 sessions (framing is a Phase 1 IV).
FRAMING: Literal["neutral"] = "neutral"

#: Rounds per session (Study 1 protocol §8 Q2).
ROUNDS: int = 35

# Derived total: 4 × 3 × 2 × 10 = 240.
TOTAL_SESSIONS: int = len(PHASE0_FAMILIES) * len(CONDITIONS) * len(DISCLOSURES) * REPLICATES


# ---------------------------------------------------------------------------
# Session manifest — deterministic ordering for reproducibility
# ---------------------------------------------------------------------------

def build_session_manifest(
    families: list[str] | None = None,
    smoke: bool = False,
) -> list[dict]:
    """Return the full ordered list of session parameter dicts.

    Each dict has: family, condition, disclosure, replicate (1-indexed).
    Ordering: family → condition → disclosure → replicate.
    Smoke mode returns 1 session per family (condition=A, disclosure=blind, replicate=1).

    Args:
        families: Restrict to these families (default: all PHASE0_FAMILIES).
        smoke:    If True, return only the first session per family.

    Returns:
        List of session parameter dicts.
    """
    target_families = families if families is not None else PHASE0_FAMILIES
    sessions = []

    if smoke:
        for family in target_families:
            sessions.append({
                "family": family,
                "condition": "A",
                "disclosure": "blind",
                "replicate": 1,
            })
        return sessions

    for family in target_families:
        for condition in CONDITIONS:
            for disclosure in DISCLOSURES:
                for rep in range(1, REPLICATES + 1):
                    sessions.append({
                        "family": family,
                        "condition": condition,
                        "disclosure": disclosure,
                        "replicate": rep,
                    })
    return sessions


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------

def _existing_session_ids(data_root: Path) -> set[str]:
    """Return the set of session_ids for already-completed sessions.

    A session is considered complete if its summary.json exists in
    ``data_root/{session_id}/summary.json``.
    """
    return {
        p.parent.name
        for p in data_root.glob("*/summary.json")
    }


def _load_completed_summaries(data_root: Path) -> list[dict]:
    """Load all existing summary.json files."""
    summaries = []
    for p in sorted(data_root.glob("*/summary.json")):
        try:
            summaries.append(json.loads(p.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            pass
    return summaries


# ---------------------------------------------------------------------------
# Cost guard helpers
# ---------------------------------------------------------------------------

def _cost_warning(total_cost: float, budget: float = 12.0) -> None:
    """Print a warning if cumulative cost exceeds 80% of the budget."""
    if total_cost >= budget * 0.80:
        pct = total_cost / budget * 100
        print(
            f"  ⚠  COST WARNING: ${total_cost:.4f} = {pct:.1f}% of ${budget:.2f} budget",
            flush=True,
        )


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_phase0(
    data_root: Path,
    smoke: bool = False,
    resume: bool = False,
    mock: bool = False,
    families: list[str] | None = None,
    budget: float = 12.0,
) -> int:
    """Run Phase 0 calibration sessions.

    Args:
        data_root:  Output directory root (data/phase0/sessions).
        smoke:      If True, run only 4 smoke sessions (1 per family).
        resume:     If True, skip sessions whose summary.json already exists.
        mock:       If True, use mock LLM responses (zero cost).
        families:   Restrict to a subset of families.
        budget:     Abort if cumulative cost exceeds this (USD).

    Returns:
        Exit code: 0 = success, 1 = one or more sessions failed.
    """
    data_root.mkdir(parents=True, exist_ok=True)
    runner = RNERunner(data_root=data_root)

    manifest = build_session_manifest(families=families, smoke=smoke)
    n_planned = len(manifest)

    if smoke:
        print(f"Phase 0 SMOKE: {n_planned} session(s) — 1 per family, condition=A, blind")
    else:
        print(f"Phase 0 FULL: {n_planned} session(s) planned")
    print(f"Output: {data_root.resolve()}")
    print("-" * 70)

    # Resume: determine which sessions are already done.
    # Since session_ids are random, we can't match by ID — instead we track
    # completion by (family, condition, disclosure, replicate) tuples recorded
    # in summary.json metadata.
    completed_keys: set[tuple] = set()
    if resume:
        for summary in _load_completed_summaries(data_root):
            meta_path = data_root / summary["session_id"] / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                key = (
                    meta.get("family_a"),
                    meta.get("condition"),
                    meta.get("disclosure"),
                    meta.get("replicate"),
                )
                completed_keys.add(key)
        if completed_keys:
            print(f"Resume: {len(completed_keys)} sessions already complete — skipping.")

    # Mock response: a valid monoculture propose (agent always proposes W→G trade).
    # Both sides hold the same resources in mono, so compatible proposals are possible.
    mock_response: str | None = None
    if mock:
        mock_response = '{"action": "propose", "give": {"W": 1}, "want": {"G": 1}}'
        print("Mock mode: zero-cost dry-run (no real API calls).")
    print("-" * 70)

    total_cost: float = 0.0
    completed: int = 0
    failed: int = 0
    skipped: int = 0
    wall_start = time.monotonic()

    for i, params in enumerate(manifest, start=1):
        family = params["family"]
        condition = params["condition"]
        disclosure = params["disclosure"]
        replicate = params["replicate"]

        session_key = (family, condition, disclosure, replicate)

        # Skip if already done (resume mode).
        if resume and session_key in completed_keys:
            skipped += 1
            continue

        label = (
            f"[{i:>3}/{n_planned}] {family:>8} cond={condition} "
            f"disc={disclosure:<10} rep={replicate:>2}"
        )
        print(f"{label} ...", end="", flush=True)

        try:
            # RNEConfig: monoculture — same family for both agents.
            config = RNEConfig(
                family_a=family,
                family_b=family,
                condition=condition,
                disclosure=disclosure,
                prompt_framing=FRAMING,
                rounds=ROUNDS,
            )
            summary = runner.run_session(config, mock_response=mock_response)

            # Persist replicate index in metadata for resume capability.
            meta_path = data_root / config.session_id / "metadata.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["replicate"] = replicate
                meta_path.write_text(json.dumps(meta, indent=2), encoding="utf-8")

            session_cost = summary.get("total_cost_usd", 0.0)
            total_cost += session_cost
            completed += 1

            trade_marker = "✓" if summary.get("completed_trades", 0) > 0 else "∅"
            print(
                f" {trade_marker} M1={summary['cooperation_rate']:.2f} "
                f"trades={summary['completed_trades']}/{ROUNDS} "
                f"parse_fails={summary.get('parse_failure_count', 0)} "
                f"cost=${session_cost:.4f}",
                flush=True,
            )

            # Cost guard: abort if over budget.
            _cost_warning(total_cost, budget)
            if total_cost > budget:
                print(
                    f"\n  ✗  BUDGET EXCEEDED: ${total_cost:.4f} > ${budget:.2f}. "
                    "Stopping. Run with --resume to continue from this point.",
                    flush=True,
                )
                return 1

        except KeyboardInterrupt:
            print("\n  Interrupted by user. Run with --resume to continue.", flush=True)
            return 1
        except Exception as exc:
            failed += 1
            print(f" FAILED: {exc}", flush=True)
            traceback.print_exc()

    elapsed = time.monotonic() - wall_start
    print("-" * 70)
    print(
        f"Phase 0 {'smoke ' if smoke else ''}complete: "
        f"{completed} done, {skipped} skipped, {failed} failed  |  "
        f"total cost=${total_cost:.4f}  |  wall={elapsed:.1f}s"
    )

    if failed > 0:
        print(f"  ✗  {failed} session(s) failed — check output above.")
        return 1

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """Parse args and run Phase 0."""
    parser = argparse.ArgumentParser(
        description=(
            "Run Phase 0 calibration: 4 families × 10 sessions × "
            "3 conditions × 2 disclosure = 240 RNE sessions."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help=(
            "Run 4 smoke sessions (1 per family, condition A, blind) "
            "to verify all providers route correctly."
        ),
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Skip sessions whose summary.json already exists.",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Use mock LLM responses (zero cost, no real API calls).",
    )
    parser.add_argument(
        "--family",
        type=str,
        default=None,
        choices=PHASE0_FAMILIES,
        help="Run only one family (useful for targeted re-runs).",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/phase0/sessions",
        help="Output directory root for session files.",
    )
    parser.add_argument(
        "--budget",
        type=float,
        default=12.0,
        help="Abort if cumulative cost exceeds this (USD).",
    )
    args = parser.parse_args()

    families = [args.family] if args.family else None

    return run_phase0(
        data_root=Path(args.data_dir),
        smoke=args.smoke,
        resume=args.resume,
        mock=args.mock,
        families=families,
        budget=args.budget,
    )


if __name__ == "__main__":
    sys.exit(main())
