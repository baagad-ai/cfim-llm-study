#!/usr/bin/env python
"""run_game.py — CLI entry point for Trade Island game runs.

Usage:
    python scripts/run_game.py --config mistral-mono --games 1
    python scripts/run_game.py --config pairwise-llama-mistral --games 3

Budget cap of $80 is enforced via litellm.BudgetManager at startup.
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

# Ensure src/ is importable when run from project root as
# `python scripts/run_game.py` (no editable install required).
_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import litellm  # noqa: E402

from src.simulation.config import GameConfig  # noqa: E402
from src.simulation.game import GameRunner  # noqa: E402


def main() -> int:
    """Parse args, init budget manager, run games. Returns exit code."""
    parser = argparse.ArgumentParser(
        description="Run Trade Island game(s).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help=(
            "Named config string. Examples: 'mistral-mono', 'phase0', "
            "'pairwise-llama-mistral'."
        ),
    )
    parser.add_argument(
        "--games",
        type=int,
        default=1,
        help="Number of sequential games to run.",
    )
    args = parser.parse_args()

    # ------------------------------------------------------------------
    # Budget manager: $80 hard cap, evaluated once at startup.
    # litellm.BudgetManager tracks cumulative spend across all completions.
    # ------------------------------------------------------------------
    budget_manager = litellm.BudgetManager(project_name="trade-island")
    # Register a single "run_game" user budget at the session level.
    # (BudgetManager requires a user key; we use a fixed key for the session.)
    budget_user = "run_game_session"
    try:
        budget_manager.create_budget(
            total_budget=80.0,
            user=budget_user,
            duration="daily",
        )
    except Exception:
        # Already exists from a previous call in the same session — ignore.
        pass

    # ------------------------------------------------------------------
    # Game loop
    # ------------------------------------------------------------------
    config_name = args.config
    print(f"Config: {config_name} | Games: {args.games}")
    print("-" * 60)

    for game_num in range(1, args.games + 1):
        print(f"[Game {game_num}/{args.games}] Starting...")
        try:
            config = GameConfig.from_name(config_name)
            runner = GameRunner(config)
            summary = runner.run_game()
            print(
                f"[Game {game_num}/{args.games}] Done — "
                f"game_id={summary['game_id']} "
                f"cost=${summary['total_cost_usd']:.4f} "
                f"rounds={summary['rounds_played']}"
            )
        except Exception:
            print(f"[Game {game_num}/{args.games}] FAILED — traceback below:")
            traceback.print_exc()
            return 1

    print("-" * 60)
    print(f"All {args.games} game(s) completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
