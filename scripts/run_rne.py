#!/usr/bin/env python
"""run_rne.py — CLI entry point for Study 1 RNE (Repeated Negotiated Exchange) sessions.

Usage::

    python scripts/run_rne.py \\
        --family-a mistral --family-b llama \\
        --condition A --disclosure blind --framing neutral --games 1

Options
-------
--family-a      Model family for Agent A (mistral | llama | gpt | gemini | ...)
--family-b      Model family for Agent B
--condition     Game condition: A (coordination) | B (mixed motive) | C (asymmetric)
--disclosure    blind | disclosed
--framing       neutral | social | strategic
--games         Number of sequential sessions to run (default: 1)
--rounds        Rounds per session (default: 35, per study protocol)
--data-dir      Output directory root (default: data/study1)
--mock          Use mock responses for dry-run / cost-free testing
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# Ensure src/ is importable when run from project root without editable install.
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from src.simulation.config import RNEConfig   # noqa: E402
from src.simulation.rne_game import RNERunner  # noqa: E402


def main() -> int:
    """Parse args, run sessions. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Run RNE (Repeated Negotiated Exchange) session(s) — Study 1.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--family-a", required=True,
                        help="Model family for Agent A (e.g. 'mistral', 'llama')")
    parser.add_argument("--family-b", required=True,
                        help="Model family for Agent B (e.g. 'llama', 'mistral')")
    parser.add_argument("--condition", required=True, choices=["A", "B", "C"],
                        help="Game condition: A=coordination, B=mixed-motive, C=asymmetric")
    parser.add_argument("--disclosure", default="blind", choices=["blind", "disclosed"],
                        help="Disclosure mode")
    parser.add_argument("--framing", default="neutral",
                        choices=["neutral", "social", "strategic"],
                        help="Prompt framing variant")
    parser.add_argument("--games", type=int, default=1,
                        help="Number of sequential sessions to run")
    parser.add_argument("--rounds", type=int, default=35,
                        help="Rounds per session")
    parser.add_argument("--data-dir", type=str, default="data/study1",
                        help="Root directory for session output")
    parser.add_argument("--mock", type=str, default=None, metavar="JSON",
                        help='Mock LLM response JSON string for cost-free dry-runs. '
                             'E.g. \'{"action":"propose","give":{"W":1},"want":{"G":1}}\'')
    args = parser.parse_args()

    data_root = Path(args.data_dir)
    runner = RNERunner(data_root=data_root)

    print(
        f"RNE study | family_a={args.family_a} family_b={args.family_b} "
        f"condition={args.condition} disclosure={args.disclosure} "
        f"framing={args.framing} rounds={args.rounds}"
    )
    print("-" * 70)

    total_cost = 0.0
    for game_num in range(1, args.games + 1):
        print(f"[Session {game_num}/{args.games}] Starting...")
        try:
            config = RNEConfig(
                family_a=args.family_a,
                family_b=args.family_b,
                condition=args.condition,
                disclosure=args.disclosure,
                prompt_framing=args.framing,
                rounds=args.rounds,
            )
            summary = runner.run_session(config, mock_response=args.mock)
            total_cost += summary.get("total_cost_usd", 0.0)
            print(
                f"[Session {game_num}/{args.games}] Done — "
                f"id={summary['session_id']} "
                f"M1(coop)={summary['cooperation_rate']:.3f} "
                f"trades={summary['completed_trades']}/{summary['total_rounds']} "
                f"cost=${summary['total_cost_usd']:.4f}"
            )
        except Exception:
            print(f"[Session {game_num}/{args.games}] FAILED — traceback below:")
            traceback.print_exc()
            return 1

    print("-" * 70)
    print(f"All {args.games} session(s) completed. Total cost: ${total_cost:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
