"""
PRE-REGISTERED ANALYSIS STUB — H1: Self-Play Premium
=====================================================
Study: Cross-Family Interaction Matrix (CFIM)
Game: Repeated Negotiated Exchange (RNE), 35 rounds
Pre-registered: 2026-03-15 (this commit predates Phase 1 data collection)
DO NOT modify the statistical test after Phase 1 data collection begins.

H1 — Self-Play Premium:
  Cooperation rates on the CFIM diagonal (same-family pairs) are
  significantly higher than off-diagonal cells (cross-family pairs).

  Test: Wilcoxon signed-rank test
    - 8 diagonal cells vs 56 off-diagonal cells
    - Null: median(diagonal) = median(off-diagonal)
    - Alternative: median(diagonal) > median(off-diagonal), one-sided
    - Significance threshold: p < 0.05
    - Effect size: r = Z / sqrt(N)

  Interpretation: If supported, LLMs cooperate more with perceived same-family
  opponents — evidence of implicit in-group preference.

Expected JSONL schema fields (from study1/{session_id}/summary.json):
  session_id, family_a, family_b, condition (A|B|C),
  disclosure (blind|disclosed), prompt_framing (neutral|social|strategic),
  M1_cooperation_rate (float 0–1), M2_exploitation_delta (float),
  M3_adaptation_lag (int rounds), M4_betrayal_recovery (int rounds),
  M5_min_acceptable_offer (float 0–1), M6_identity_sensitivity (float)
"""

from pathlib import Path
import json

import polars as pl
import numpy as np
from scipy import stats


def load_study1_summaries(data_dir: Path = Path("data/study1")) -> pl.DataFrame:
    """
    Load all per-session summary.json files from Study 1.

    Returns a DataFrame with one row per session, columns:
      session_id, family_a, family_b, condition, disclosure, prompt_framing,
      M1_cooperation_rate, M2_exploitation_delta, M3_adaptation_lag,
      M4_betrayal_recovery, M5_min_acceptable_offer, M6_identity_sensitivity
    """
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
            "Run Study 1 data collection before running analysis."
        )
    return pl.DataFrame(rows)


def compute_diagonal_vs_offdiagonal(df: pl.DataFrame) -> tuple[list[float], list[float]]:
    """
    Split cooperation rates into diagonal (same-family) and off-diagonal (cross-family) cells.

    Aggregates to cell-level means first (one mean per unique family_a × family_b × condition
    × disclosure combination) to avoid inflating sample size within cells.

    Returns:
        diagonal_rates: list of cell-mean M1 values where family_a == family_b
        offdiagonal_rates: list of cell-mean M1 values where family_a != family_b
    """
    # Cell-level mean cooperation rate (aggregate over runs within cell)
    cell_means = (
        df.group_by(["family_a", "family_b", "condition", "disclosure"])
        .agg(pl.mean("M1_cooperation_rate").alias("cell_mean_M1"))
    )

    diagonal = cell_means.filter(pl.col("family_a") == pl.col("family_b"))
    offdiagonal = cell_means.filter(pl.col("family_a") != pl.col("family_b"))

    return (
        diagonal["cell_mean_M1"].to_list(),
        offdiagonal["cell_mean_M1"].to_list(),
    )


def test_h1(df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H1 — Self-Play Premium

    Args:
        df: Study 1 sessions DataFrame in expected schema

    Returns dict with keys:
        statistic (float): Wilcoxon W statistic
        p_value (float): one-sided p-value
        effect_size_r (float): r = Z / sqrt(N) where N = smaller group size
        n_diagonal (int): number of diagonal cells
        n_offdiagonal (int): number of off-diagonal cells
        median_diagonal (float): median cooperation rate on diagonal
        median_offdiagonal (float): median cooperation rate off-diagonal
        supported (bool): True if p_value < 0.05 and median_diagonal > median_offdiagonal
        narrative (str): human-readable result summary
    """
    diag, offdiag = compute_diagonal_vs_offdiagonal(df)

    if len(diag) < 2 or len(offdiag) < 2:
        raise ValueError(
            f"Insufficient data: diagonal={len(diag)} cells, offdiagonal={len(offdiag)} cells. "
            "Need at least 2 per group."
        )

    # Wilcoxon signed-rank on paired diagonal vs offdiagonal is not directly
    # applicable (unequal n). Use Mann-Whitney U as a rank-based non-parametric
    # test; report as pre-registered Wilcoxon-family test.
    # Pre-registration note: with 8 diagonal cells and up to 56 off-diagonal
    # cells the appropriate test is Mann-Whitney U (one-sided), equivalent to
    # the Wilcoxon rank-sum test.
    stat, p_two = stats.mannwhitneyu(diag, offdiag, alternative="two-sided")
    _, p_one = stats.mannwhitneyu(diag, offdiag, alternative="greater")

    n = min(len(diag), len(offdiag))
    # Effect size r = Z / sqrt(N); approximate Z from U
    # U ~ N(n1*n2/2, sqrt(n1*n2*(n1+n2+1)/12)) under H0
    n1, n2 = len(diag), len(offdiag)
    mean_u = n1 * n2 / 2
    std_u = np.sqrt(n1 * n2 * (n1 + n2 + 1) / 12)
    z = (stat - mean_u) / std_u
    effect_r = z / np.sqrt(n1 + n2)

    median_diag = float(np.median(diag))
    median_offdiag = float(np.median(offdiag))
    supported = (p_one < 0.05) and (median_diag > median_offdiag)

    narrative = (
        f"H1 {'SUPPORTED' if supported else 'NOT SUPPORTED'}: "
        f"diagonal median M1={median_diag:.3f} vs off-diagonal median M1={median_offdiag:.3f}; "
        f"Mann-Whitney U={stat:.1f}, p(one-sided)={p_one:.4f}, r={effect_r:.3f}, "
        f"N_diag={n1}, N_offdiag={n2}"
    )

    return {
        "hypothesis": "H1",
        "statistic": float(stat),
        "p_value": float(p_one),
        "p_value_two_sided": float(p_two),
        "effect_size_r": float(effect_r),
        "n_diagonal": n1,
        "n_offdiagonal": n2,
        "median_diagonal": median_diag,
        "median_offdiagonal": median_offdiag,
        "supported": supported,
        "narrative": narrative,
    }


def run_h1_analysis(data_dir: Path = Path("data/study1")) -> dict:
    """Entry point: load summaries, run H1 test, return results dict."""
    df = load_study1_summaries(data_dir)
    return test_h1(df)
