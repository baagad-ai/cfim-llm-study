"""
PRE-REGISTERED ANALYSIS STUB — H3
H3: VP ratio deviates from 1.0 for ≥2 of 6 pairwise conditions.
Test: one-sample t-test per condition, BH-corrected across 6 comparisons.

STATUS: STUB — committed before data collection.
"""

import polars as pl
import numpy as np
from scipy import stats
from pathlib import Path


def compute_vp_ratio(df: pl.DataFrame, pairing: str) -> list[float]:
    """
    Compute VP ratio (model_A VP / model_B VP) for each game in a pairwise condition.
    Ratio > 1.0 → model A outperforms. Ratio < 1.0 → model B outperforms.
    """
    raise NotImplementedError("TODO: implement after JSONL schema finalized")


def test_h3(df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H3
    One-sample t-test per pairwise condition (null: VP ratio = 1.0).
    BH correction applied across 6 simultaneous comparisons.
    H3 supported if ≥2 conditions survive correction.

    Args:
        df: DataFrame with Phase 2 game outcomes [game_id, pairing, model_a_vp, model_b_vp]

    Returns:
        dict with per-pairing t-statistics, raw p-values, BH-corrected p-values
    """
    PAIRINGS = [
        "llama_deepseek",
        "llama_gemini",
        "llama_mistral",
        "deepseek_gemini",
        "deepseek_mistral",
        "gemini_mistral",
    ]

    results = {}
    raw_pvalues = []

    for pairing in PAIRINGS:
        # TODO: compute_vp_ratio(df, pairing)
        ratios = []  # placeholder
        if ratios:
            t_stat, p_val = stats.ttest_1samp(ratios, popmean=1.0)
        else:
            t_stat, p_val = float("nan"), float("nan")

        results[pairing] = {
            "t_statistic": t_stat,
            "p_value_raw": p_val,
            "mean_ratio": float(np.mean(ratios)) if ratios else None,
            "n_games": len(ratios),
        }
        raw_pvalues.append(p_val)

    # BH correction
    from statsmodels.stats.multitest import multipletests
    reject, p_adj, _, _ = multipletests(raw_pvalues, method="fdr_bh")

    for i, pairing in enumerate(PAIRINGS):
        results[pairing]["p_value_bh"] = p_adj[i]
        results[pairing]["significant_bh"] = bool(reject[i])

    n_significant = sum(1 for r in results.values() if r["significant_bh"])

    return {
        "hypothesis": "H3",
        "test": "one-sample t-test + BH correction",
        "n_pairings": len(PAIRINGS),
        "n_significant": n_significant,
        "threshold": 2,  # ≥2 conditions must be significant
        "result": "SUPPORTED" if n_significant >= 2 else "NOT SUPPORTED",
        "per_pairing": results,
    }


if __name__ == "__main__":
    print("H3 Analysis Stub — VP Ratio t-test + BH Correction")
    print("Pre-registration timestamp:", __import__("datetime").datetime.utcnow().isoformat())
