"""
PRE-REGISTERED ANALYSIS STUB — H5: CFIM Patterns Predict Multi-Agent Outcomes
==============================================================================
Study: Cross-Family Interaction Matrix (CFIM) — Study 2 (Harbour) validation
Game: Harbour 6-agent resource game, 30 rounds
Pre-registered: 2026-03-15 (this commit predates Phase 1 data collection)
DO NOT modify the statistical test after Phase 1 data collection begins.

H5 — CFIM Patterns Predict Multi-Agent Outcomes:
  In Study 2 mixed-composition Harbour games, the mean bilateral cooperation
  rate from Study 1 for the specific family pairs present in the game predicts
  final Victory Point (VP) variance across agents.

  Test: OLS linear regression
    dependent variable: VP variance across agents at end of Harbour game
                        (higher variance = more unequal outcomes)
    predictor: mean_bilateral_M1 = mean M1 cooperation rate from Study 1
                CFIM cells for all family-pair combinations present in the
                Harbour game composition
    threshold: R² > 0.15 AND p < 0.05 for the predictor coefficient

  Interpretation: If supported, bilateral behavioral fingerprints from clean
  dyadic games generalise to predict emergent inequality in complex
  multi-agent settings. A mixed composition where some family-pairs show
  high exploitation (low M1) should produce higher VP variance (unfair outcomes).

  This is the ecological validity bridge between Study 1 (mechanism) and
  Study 2 (complex multi-agent realism).

Expected data schemas:

  Study 2 game summaries (data/study2/{game_id}/summary.json):
    game_id, composition (mono|mixed), agent_families (list[str]),
    final_vp_per_agent (dict agent_id → vp),
    vp_variance (float), vp_gini (float)

  Study 1 CFIM matrix (output of h1/h2 analysis, or direct from summaries):
    family_a, family_b → mean_M1_blind, mean_M1_disclosed
"""

from pathlib import Path
import json
from itertools import combinations

import polars as pl
import numpy as np


def load_study2_summaries(data_dir: Path = Path("data/study2")) -> pl.DataFrame:
    """Load per-game summary.json files from Study 2."""
    rows = []
    for summary_path in sorted(data_dir.glob("*/summary.json")):
        try:
            d = json.loads(summary_path.read_text())
            rows.append(d)
        except Exception as e:
            print(f"WARNING: skipping {summary_path}: {e}")
    if not rows:
        raise FileNotFoundError(
            f"No summary.json files found under {data_dir}. "
            "Run Study 2 (Harbour) data collection before running H5."
        )
    return pl.DataFrame(rows)


def load_cfim_matrix(data_dir: Path = Path("data/study1")) -> dict[tuple[str, str], float]:
    """
    Build CFIM matrix from Study 1 summaries.

    Returns dict mapping (family_a, family_b) → mean M1_cooperation_rate
    (averaged over blind condition only, to isolate intrinsic cooperation
    tendencies independent of disclosure effects).
    """
    from src.analysis.h1_self_play_premium import load_study1_summaries

    df = load_study1_summaries(data_dir)
    blind = df.filter(pl.col("disclosure") == "blind")

    cell_means = (
        blind.group_by(["family_a", "family_b"])
        .agg(pl.mean("M1_cooperation_rate").alias("mean_M1"))
    )

    return {
        (row["family_a"], row["family_b"]): row["mean_M1"]
        for row in cell_means.to_dicts()
    }


def compute_game_predicted_m1(
    agent_families: list[str],
    cfim: dict[tuple[str, str], float],
) -> float:
    """
    Compute the mean CFIM M1 for all family pairs present in a Harbour game.

    For each unique ordered pair (family_a, family_b) from agent_families,
    look up the M1 value from the CFIM. Symmetric lookup: if (a, b) not found
    try (b, a). Average across all pairs present.

    Returns float (mean predicted cooperation) or NaN if CFIM is empty/all missing.
    """
    pair_m1_values = []
    for fa, fb in combinations(agent_families, 2):
        m1 = cfim.get((fa, fb), cfim.get((fb, fa), None))
        if m1 is not None:
            pair_m1_values.append(m1)

    return float(np.mean(pair_m1_values)) if pair_m1_values else float("nan")


def test_h5(
    df_study2: pl.DataFrame,
    cfim: dict[tuple[str, str], float],
) -> dict:
    """
    PRE-REGISTERED TEST: H5 — CFIM Patterns Predict Multi-Agent Outcomes

    Args:
        df_study2: Study 2 game summaries DataFrame
        cfim: CFIM matrix from Study 1 {(family_a, family_b): mean_M1}

    Returns dict with:
        r_squared, p_value, beta (coefficient), intercept,
        n_games, supported (bool), narrative (str)
    """
    from scipy import stats as scipy_stats

    # Build (predicted_m1, vp_variance) pairs
    predicted = []
    outcomes = []

    for row in df_study2.to_dicts():
        families = row.get("agent_families", [])
        vp_var = row.get("vp_variance")
        if not families or vp_var is None:
            continue
        pred_m1 = compute_game_predicted_m1(families, cfim)
        if not np.isnan(pred_m1):
            predicted.append(pred_m1)
            outcomes.append(float(vp_var))

    n = len(predicted)
    if n < 5:
        raise ValueError(
            f"Insufficient Study 2 games with CFIM coverage for H5: n={n}. "
            "Need at least 5 mixed-composition games."
        )

    pred_arr = np.array(predicted)
    out_arr = np.array(outcomes)

    slope, intercept, r_value, p_value, se = scipy_stats.linregress(pred_arr, out_arr)
    r_sq = r_value ** 2

    supported = (p_value < 0.05) and (r_sq > 0.15)

    narrative = (
        f"H5 {'SUPPORTED' if supported else 'NOT SUPPORTED'}: "
        f"R²={r_sq:.3f} ({'exceeds' if r_sq > 0.15 else 'below'} threshold 0.15), "
        f"β={slope:.4f}, p={p_value:.4f}, n={n} mixed-composition games. "
        f"{'Higher bilateral cooperation predicts lower VP variance' if slope < 0 else 'Higher bilateral cooperation predicts higher VP variance (unexpected direction)'}."
    )

    return {
        "hypothesis": "H5",
        "r_squared": float(r_sq),
        "r_value": float(r_value),
        "beta": float(slope),
        "intercept": float(intercept),
        "std_error": float(se),
        "p_value": float(p_value),
        "n_games": n,
        "supported": supported,
        "narrative": narrative,
    }


def run_h5_analysis(
    study1_dir: Path = Path("data/study1"),
    study2_dir: Path = Path("data/study2"),
) -> dict:
    """
    Entry point: load Study 2 data and Study 1 CFIM matrix, run H5 test.
    """
    df_study2 = load_study2_summaries(study2_dir)

    # Filter to mixed-composition games only (mono games aren't meaningful for H5)
    mixed = df_study2.filter(pl.col("composition") == "mixed")
    if len(mixed) == 0:
        raise ValueError("No mixed-composition Study 2 games found. H5 requires mixed games.")

    cfim = load_cfim_matrix(study1_dir)
    return test_h5(mixed, cfim)
