"""
PRE-REGISTERED ANALYSIS STUB — H1
H1: Gini coefficient at round 25 differs across 4 families (Kruskal-Wallis, α=0.05)

STATUS: STUB — committed before data collection per OSF pre-registration.
DO NOT modify the test logic after Phase 1 data collection begins.
"""

import polars as pl
from scipy import stats
from pathlib import Path


def load_phase1_data(data_dir: Path) -> pl.DataFrame:
    """
    Load Phase 1 monoculture game logs.
    Expected schema: [game_id, model_family, round, agent_id, vp, inventory_value, ...]
    TODO: implement once JSONL schema is finalized in M001/S02.
    """
    raise NotImplementedError("TODO: implement data loading after JSONL schema finalized")


def compute_gini(values: list[float]) -> float:
    """Compute Gini coefficient for a list of values (e.g., VP at round 25)."""
    if not values or len(values) < 2:
        return 0.0
    values = sorted(values)
    n = len(values)
    cumsum = sum((i + 1) * v for i, v in enumerate(values))
    return (2 * cumsum) / (n * sum(values)) - (n + 1) / n


def test_h1(df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H1
    Kruskal-Wallis test on Gini coefficient at round 25 across 4 model families.
    α = 0.05. BH correction not applied (single omnibus test).

    Args:
        df: DataFrame with columns [game_id, model_family, round, agent_id, vp]

    Returns:
        dict with keys: h_statistic, p_value, significant, effect_size_eta_sq
    """
    # Filter to round 25 only
    final_round = df.filter(pl.col("round") == 25)

    # Compute Gini per game
    gini_per_game = (
        final_round
        .group_by(["game_id", "model_family"])
        .agg(pl.col("vp").apply(compute_gini).alias("gini"))
    )

    # Get per-family Gini distributions
    families = gini_per_game["model_family"].unique().to_list()
    groups = [
        gini_per_game.filter(pl.col("model_family") == fam)["gini"].to_list()
        for fam in families
    ]

    # Kruskal-Wallis test
    h_stat, p_value = stats.kruskal(*groups)

    # Effect size: eta-squared = (H - k + 1) / (N - k)
    k = len(families)
    N = sum(len(g) for g in groups)
    eta_sq = (h_stat - k + 1) / (N - k) if N > k else None

    return {
        "hypothesis": "H1",
        "test": "Kruskal-Wallis",
        "families_tested": families,
        "h_statistic": h_stat,
        "p_value": p_value,
        "alpha": 0.05,
        "significant": p_value < 0.05,
        "effect_size_eta_sq": eta_sq,
        "n_games_per_family": {fam: len(g) for fam, g in zip(families, groups)},
        "result": "SUPPORTED" if p_value < 0.05 else "NOT SUPPORTED",
    }


if __name__ == "__main__":
    print("H1 Analysis Stub — Kruskal-Wallis on Gini Coefficient")
    print("This stub will be implemented with real data in M004/S01.")
    print("Pre-registration timestamp:", __import__("datetime").datetime.utcnow().isoformat())
