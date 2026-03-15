"""
PRE-REGISTERED ANALYSIS STUB — H4: Adaptation Lag Differs by Family Pair
=========================================================================
Study: Cross-Family Interaction Matrix (CFIM)
Game: Repeated Negotiated Exchange (RNE), 35 rounds, perturbation at round 20
Pre-registered: 2026-03-15 (this commit predates Phase 1 data collection)
DO NOT modify the statistical test after Phase 1 data collection begins.

H4 — Adaptation Lag Differs by Family Pair:
  M3 (adaptation lag) varies significantly across the 36 unique pairings.

  Test: Kruskal-Wallis test across 28 unique pairings (7 families, upper
        triangle + diagonal, de-duplicating A×B = B×A)
  Significance: p < 0.05
  Effect size: η² (eta-squared) = (H - k + 1) / (n - k)
  Pre-specified effect size threshold: η² > 0.10

  Both p < 0.05 AND η² > 0.10 must hold for H4 to be supported.

  Interpretation: If supported, some family combinations produce faster/slower
  strategic adaptation — structural rigidity is pair-specific, not solely
  family-specific. This is relevant for deployment safety: a rigid model won't
  de-escalate from a defective opponent.

  M3 definition: Number of rounds after the perturbation (round 20) until the
  focal agent's action pattern changes significantly (3+ consecutive rounds of
  altered trade proposal rate, threshold ≥ 0.30 absolute change from baseline).
  M3 = NaN if the agent never adapted within the 15 post-perturbation rounds.
  NaN values are excluded from the test (missing-at-random assumption); NaN
  rate itself is a secondary metric reported alongside H4.

Expected JSONL schema fields (from study1/{session_id}/summary.json):
  session_id, family_a, family_b, condition, disclosure, prompt_framing,
  M3_adaptation_lag (int or null — rounds to adaptation, null if never adapted)
"""

from pathlib import Path
import json

import polars as pl
import numpy as np
from scipy import stats


def load_study1_summaries(data_dir: Path = Path("data/study1")) -> pl.DataFrame:
    """Load per-session summary.json files."""
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


def canonical_pairing(family_a: str, family_b: str) -> str:
    """Return a canonical pairing key (alphabetical order) to de-duplicate A×B = B×A."""
    return "_".join(sorted([family_a, family_b]))


def compute_adaptation_lag_by_pairing(df: pl.DataFrame) -> dict[str, list[float]]:
    """
    Group M3_adaptation_lag values by canonical pairing.
    Excludes null/NaN values (agent never adapted).

    Returns:
        dict mapping canonical_pairing → list of M3 values (excluding NaN)
        and separately reports nan_rate per pairing.
    """
    df_lag = df.with_columns(
        pl.struct(["family_a", "family_b"])
        .map_elements(lambda s: canonical_pairing(s["family_a"], s["family_b"]),
                      return_dtype=pl.Utf8)
        .alias("canonical_pairing")
    )

    # Filter to sessions with valid M3 (adaptation occurred)
    has_lag = df_lag.filter(pl.col("M3_adaptation_lag").is_not_null())

    pairing_groups: dict[str, list[float]] = {}
    nan_rates: dict[str, float] = {}

    all_pairings = df_lag["canonical_pairing"].unique().to_list()
    for pair in sorted(all_pairings):
        subset = df_lag.filter(pl.col("canonical_pairing") == pair)
        valid = subset.filter(pl.col("M3_adaptation_lag").is_not_null())
        pairing_groups[pair] = valid["M3_adaptation_lag"].cast(pl.Float64).to_list()
        n_total = len(subset)
        n_nan = n_total - len(valid)
        nan_rates[pair] = n_nan / n_total if n_total > 0 else float("nan")

    return pairing_groups, nan_rates


def test_h4(df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H4 — Adaptation Lag Differs by Family Pair

    Args:
        df: Study 1 summaries DataFrame in expected schema

    Returns dict with:
        kruskal_h (float), kruskal_p (float), eta_squared (float),
        k_pairings (int), n_total_valid (int),
        supported (bool), narrative (str),
        per_pairing_medians (dict), nan_rates (dict)
    """
    pairing_groups, nan_rates = compute_adaptation_lag_by_pairing(df)

    # Filter to pairings with ≥ 3 valid observations
    valid_groups = {k: v for k, v in pairing_groups.items() if len(v) >= 3}
    k = len(valid_groups)
    n_total = sum(len(v) for v in valid_groups.values())

    if k < 2:
        raise ValueError(
            f"Need ≥ 2 pairings with ≥3 valid M3 observations for Kruskal-Wallis. "
            f"Got k={k}. Check that perturbation events are logged correctly."
        )

    h_stat, p_value = stats.kruskal(*valid_groups.values())

    # η² = (H - k + 1) / (n - k), where H = Kruskal-Wallis statistic
    eta_sq = (h_stat - k + 1) / (n_total - k) if n_total > k else float("nan")
    eta_sq = max(0.0, eta_sq)  # floor at 0 (can be slightly negative due to correction)

    per_pairing_medians = {
        pair: float(np.median(vals))
        for pair, vals in valid_groups.items()
    }

    supported = (p_value < 0.05) and (eta_sq > 0.10)

    narrative = (
        f"H4 {'SUPPORTED' if supported else 'NOT SUPPORTED'}: "
        f"Kruskal-Wallis H({k-1})={h_stat:.3f}, p={p_value:.4f}, "
        f"η²={eta_sq:.3f} ({'exceeds' if eta_sq > 0.10 else 'below'} threshold 0.10); "
        f"k={k} pairings, n={n_total} valid sessions"
    )

    return {
        "hypothesis": "H4",
        "kruskal_h": float(h_stat),
        "kruskal_df": k - 1,
        "kruskal_p": float(p_value),
        "eta_squared": float(eta_sq),
        "k_pairings": k,
        "n_total_valid": n_total,
        "supported": supported,
        "narrative": narrative,
        "per_pairing_medians": per_pairing_medians,
        "nan_rates": nan_rates,
    }


def run_h4_analysis(data_dir: Path = Path("data/study1")) -> dict:
    """Entry point: load summaries, run H4 test, return results dict."""
    df = load_study1_summaries(data_dir)
    return test_h4(df)
