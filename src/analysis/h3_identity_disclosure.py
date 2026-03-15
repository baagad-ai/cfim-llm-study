"""
PRE-REGISTERED ANALYSIS STUB — H3: Identity Disclosure Amplifies Behavioral Divergence
=======================================================================================
Study: Cross-Family Interaction Matrix (CFIM)
Game: Repeated Negotiated Exchange (RNE), 35 rounds
Pre-registered: 2026-03-15 (this commit predates Phase 1 data collection)
DO NOT modify the statistical test after Phase 1 data collection begins.

H3 — Identity Disclosure Amplifies Behavioral Divergence:
  Part A: Mean |M6| (identity sensitivity) > 0 across all pairings.
    Test: one-sample t-test, H0: mean(|M6|) = 0, one-sided (greater), p < 0.05
    M6 = |M1_disclosed - M1_blind| for each session pair matched by
         family_a, family_b, condition, prompt_framing, random_seed

  Part B: M6 is larger for cross-family pairs than same-family pairs.
    Test: paired Wilcoxon signed-rank test on cell-level |M6| means,
    one-sided (cross > same), p < 0.05

  NOTE on direction: Per design resolution (SIMULATION_DESIGN.md §8, Q1),
  the direction of M6 is NOT pre-specified as positive. Disclosure may
  increase OR decrease cooperation depending on framing condition.
  H3 tests whether the *magnitude* of disclosure effects is non-zero
  and larger for cross-family pairs. Both tests must pass for H3 to be
  supported.

  Interpretation: If supported, LLMs use opponent family labels to adjust
  strategy (Part A) and this adjustment is larger when the opponent is a
  different family (Part B).

Expected JSONL schema fields (from study1/{session_id}/summary.json):
  session_id, family_a, family_b, condition, disclosure (blind|disclosed),
  prompt_framing, random_seed, M1_cooperation_rate, M6_identity_sensitivity
"""

from pathlib import Path

import polars as pl
import numpy as np
from scipy import stats


def load_study1_summaries(data_dir: Path = Path("data/study1")) -> pl.DataFrame:
    """
    Load per-session summary.json files. Returns DataFrame with one row per session.
    """
    import json
    rows = []
    for summary_path in sorted(data_dir.glob("*/summary.json")):
        try:
            d = json.loads(summary_path.read_text())
            rows.append(d)
        except Exception as e:
            print(f"WARNING: skipping {summary_path}: {e}")
    if not rows:
        raise FileNotFoundError(
            f"No summary.json files found under {data_dir}."
        )
    return pl.DataFrame(rows)


def compute_identity_sensitivity(df: pl.DataFrame) -> pl.DataFrame:
    """
    Compute M6 = |M1_disclosed - M1_blind| for each matched session pair.

    Matching key: family_a, family_b, condition, prompt_framing, random_seed
    Sessions must come in blind/disclosed pairs with the same random_seed.

    Returns DataFrame with columns:
      family_a, family_b, condition, prompt_framing, random_seed,
      M1_blind, M1_disclosed, M6_abs (absolute identity sensitivity),
      is_same_family (bool)
    """
    blind = df.filter(pl.col("disclosure") == "blind").select([
        "family_a", "family_b", "condition", "prompt_framing", "random_seed",
        pl.col("M1_cooperation_rate").alias("M1_blind"),
    ])
    disclosed = df.filter(pl.col("disclosure") == "disclosed").select([
        "family_a", "family_b", "condition", "prompt_framing", "random_seed",
        pl.col("M1_cooperation_rate").alias("M1_disclosed",)
    ])

    matched = blind.join(
        disclosed,
        on=["family_a", "family_b", "condition", "prompt_framing", "random_seed"],
        how="inner",
    )

    matched = matched.with_columns([
        (pl.col("M1_disclosed") - pl.col("M1_blind")).alias("M6_signed"),
        (pl.col("M1_disclosed") - pl.col("M1_blind")).abs().alias("M6_abs"),
        (pl.col("family_a") == pl.col("family_b")).alias("is_same_family"),
    ])

    return matched


def test_h3_part_a(matched: pl.DataFrame) -> dict:
    """
    Part A: one-sample t-test that mean |M6| > 0.
    """
    m6_values = matched["M6_abs"].to_list()
    n = len(m6_values)
    if n < 3:
        raise ValueError(f"Insufficient matched pairs for H3 Part A: n={n}")

    t_stat, p_two = stats.ttest_1samp(m6_values, popmean=0)
    p_one = p_two / 2 if t_stat > 0 else 1.0 - p_two / 2

    mean_m6 = float(np.mean(m6_values))
    supported = (p_one < 0.05) and (mean_m6 > 0)

    return {
        "part": "A",
        "test": "one_sample_t",
        "n_pairs": n,
        "mean_M6_abs": mean_m6,
        "std_M6_abs": float(np.std(m6_values, ddof=1)),
        "t_statistic": float(t_stat),
        "p_value_one_sided": float(p_one),
        "supported": supported,
        "narrative": (
            f"H3-A {'SUPPORTED' if supported else 'NOT SUPPORTED'}: "
            f"mean|M6|={mean_m6:.4f}, t({n-1})={t_stat:.3f}, p={p_one:.4f}"
        ),
    }


def test_h3_part_b(matched: pl.DataFrame) -> dict:
    """
    Part B: Wilcoxon/Mann-Whitney on cell-level |M6|, cross > same.
    """
    # Aggregate to cell level
    cell_m6 = (
        matched.group_by(["family_a", "family_b", "is_same_family"])
        .agg(pl.mean("M6_abs").alias("cell_mean_M6"))
    )

    same = cell_m6.filter(pl.col("is_same_family"))["cell_mean_M6"].to_list()
    cross = cell_m6.filter(~pl.col("is_same_family"))["cell_mean_M6"].to_list()

    if len(same) < 2 or len(cross) < 2:
        raise ValueError(
            f"Insufficient cells for H3 Part B: same={len(same)}, cross={len(cross)}"
        )

    stat, p_two = stats.mannwhitneyu(cross, same, alternative="two-sided")
    _, p_one = stats.mannwhitneyu(cross, same, alternative="greater")

    median_cross = float(np.median(cross))
    median_same = float(np.median(same))
    supported = (p_one < 0.05) and (median_cross > median_same)

    return {
        "part": "B",
        "test": "mann_whitney_u",
        "n_same_cells": len(same),
        "n_cross_cells": len(cross),
        "median_M6_same": median_same,
        "median_M6_cross": median_cross,
        "u_statistic": float(stat),
        "p_value_one_sided": float(p_one),
        "supported": supported,
        "narrative": (
            f"H3-B {'SUPPORTED' if supported else 'NOT SUPPORTED'}: "
            f"median|M6| cross={median_cross:.4f} vs same={median_same:.4f}, "
            f"U={stat:.1f}, p={p_one:.4f}"
        ),
    }


def test_h3(df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H3 — Identity Disclosure Amplifies Behavioral Divergence
    Both parts must pass for H3 to be supported.
    """
    matched = compute_identity_sensitivity(df)
    result_a = test_h3_part_a(matched)
    result_b = test_h3_part_b(matched)

    supported = result_a["supported"] and result_b["supported"]

    return {
        "hypothesis": "H3",
        "supported": supported,
        "part_a": result_a,
        "part_b": result_b,
        "n_matched_pairs": len(matched),
        "narrative": (
            f"H3 {'SUPPORTED' if supported else 'NOT SUPPORTED'} "
            f"(Part A: {result_a['supported']}, Part B: {result_b['supported']})"
        ),
    }


def run_h3_analysis(data_dir: Path = Path("data/study1")) -> dict:
    """Entry point: load summaries, run H3 test, return results dict."""
    df = load_study1_summaries(data_dir)
    return test_h3(df)
