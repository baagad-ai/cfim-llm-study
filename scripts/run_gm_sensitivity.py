#!/usr/bin/env python
"""run_gm_sensitivity.py — Run Llama-GM sensitivity games for Phase 0 confound quantification.

Runs N phase0 games using Llama as the GM model instead of the default Mistral GM.
This enables GM-confound analysis: comparing outcomes between Mistral-GM and Llama-GM
games controls for whether GM parse quality affects trade acceptance rates.

Usage:
    python scripts/run_gm_sensitivity.py --games 10
    python scripts/run_gm_sensitivity.py --games 10 --dry-run
"""

from __future__ import annotations

import argparse
import sys
import traceback
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import litellm  # noqa: E402

from src.simulation.config import GameConfig  # noqa: E402
from src.simulation.game import GameRunner  # noqa: E402

# Llama model used as GM in sensitivity games
_LLAMA_GM_MODEL = "groq/llama-3.3-70b-versatile"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run Llama-GM sensitivity games for Phase 0 confound quantification.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--games",
        type=int,
        default=10,
        help="Number of Llama-GM sensitivity games to run.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print config and exit without running games.",
    )
    args = parser.parse_args()

    # Build config: phase0 agent mix + llama as GM
    config = GameConfig.from_name("phase0")
    config = config.model_copy(update={"gm_model": _LLAMA_GM_MODEL})

    if args.dry_run:
        print(f"DRY RUN — would run {args.games} games with config:")
        print(f"  config_name: {config.config_name}")
        print(f"  gm_model:    {config.gm_model}")
        print(f"  agents:      {[a['model_family'] for a in config.agent_models]}")
        return 0

    print(f"Llama-GM sensitivity: {args.games} games")
    print(f"GM model: {_LLAMA_GM_MODEL}")
    print(f"Agent mix: {[a['model_family'] for a in config.agent_models]}")
    print("-" * 60)

    # Budget guard
    budget_manager = litellm.BudgetManager(project_name="trade-island")
    budget_user = "sensitivity_session"
    try:
        budget_manager.create_budget(
            total_budget=80.0,
            user=budget_user,
            duration="daily",
        )
    except Exception:
        pass

    for game_num in range(1, args.games + 1):
        print(f"[Sensitivity {game_num}/{args.games}] Starting (Llama-GM)...")
        try:
            # Re-build config each game for fresh randomization
            cfg = GameConfig.from_name("phase0")
            cfg = cfg.model_copy(update={"gm_model": _LLAMA_GM_MODEL})
            runner = GameRunner(cfg)
            summary = runner.run_game()
            print(
                f"[Sensitivity {game_num}/{args.games}] Done — "
                f"game_id={summary['game_id']} "
                f"cost=${summary['total_cost_usd']:.4f} "
                f"rounds={summary['rounds_played']}"
            )
        except Exception:
            print(f"[Sensitivity {game_num}/{args.games}] FAILED:")
            traceback.print_exc()
            return 1

    print("-" * 60)
    print(f"All {args.games} sensitivity game(s) completed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
