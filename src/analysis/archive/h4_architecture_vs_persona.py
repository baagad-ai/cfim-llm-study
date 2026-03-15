"""
PRE-REGISTERED ANALYSIS STUB — H4
H4: Architecture variance > persona variance on ≥3 of 5 pre-specified metrics.
Test: permutation-based variance comparison.

Metrics:
  1. VP at round 25
  2. Trade acceptance rate
  3. Gini coefficient
  4. Exploitation index
  5. Cooperation tendency score

STATUS: STUB — committed before data collection.
"""

import polars as pl
import numpy as np
from pathlib import Path

METRICS = [
    "vp_round25",
    "trade_acceptance_rate",
    "gini_coefficient",
    "exploitation_index",
    "cooperation_tendency_score",
]


def permutation_variance_test(
    arch_values: list[float],
    persona_values: list[float],
    n_permutations: int = 10_000,
    random_seed: int = 42,
) -> dict:
    """
    Permutation test: is Var(arch_values) > Var(persona_values)?
    Null hypothesis: Var(arch) <= Var(persona).
    One-sided p-value: proportion of permutations where permuted Var(arch) >= observed Var(arch).
    """
    rng = np.random.default_rng(random_seed)

    observed_var_arch = np.var(arch_values, ddof=1)
    observed_var_persona = np.var(persona_values, ddof=1)
    observed_diff = observed_var_arch - observed_var_persona

    # Permutation: pool all values, randomly split into two groups of same size
    pooled = np.array(arch_values + persona_values)
    n_arch = len(arch_values)

    count_extreme = 0
    for _ in range(n_permutations):
        rng.shuffle(pooled)
        perm_arch = pooled[:n_arch]
        perm_persona = pooled[n_arch:]
        perm_diff = np.var(perm_arch, ddof=1) - np.var(perm_persona, ddof=1)
        if perm_diff >= observed_diff:
            count_extreme += 1

    p_value = count_extreme / n_permutations

    return {
        "var_architecture": float(observed_var_arch),
        "var_persona": float(observed_var_persona),
        "observed_diff": float(observed_diff),
        "p_value": p_value,
        "significant": p_value < 0.05,
        "arch_wins": observed_var_arch > observed_var_persona,
    }


def test_h4(arch_df: pl.DataFrame, persona_df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H4
    Compare variance across 5 metrics: architecture condition vs persona condition.
    H4 supported if architecture variance > persona variance on ≥3 of 5 metrics.

    Args:
        arch_df: Phase 2B architecture condition results [game_id, metric_name, value]
        persona_df: Phase 2B persona condition results [game_id, metric_name, value]

    Returns:
        dict with per-metric test results and overall H4 verdict
    """
    results = {}
    wins = 0

    for metric in METRICS:
        # TODO: extract metric values from dataframes
        arch_values = []    # placeholder
        persona_values = [] # placeholder

        if arch_values and persona_values:
            test_result = permutation_variance_test(arch_values, persona_values)
        else:
            test_result = {
                "var_architecture": None,
                "var_persona": None,
                "p_value": None,
                "significant": False,
                "arch_wins": False,
            }

        results[metric] = test_result
        if test_result["arch_wins"] and test_result.get("significant", False):
            wins += 1

    return {
        "hypothesis": "H4",
        "test": "permutation variance comparison (10,000 permutations, seed=42)",
        "metrics_tested": METRICS,
        "n_metrics_arch_wins": wins,
        "threshold": 3,  # ≥3 metrics must show arch > persona
        "result": "SUPPORTED" if wins >= 3 else "NOT SUPPORTED",
        "per_metric": results,
    }


if __name__ == "__main__":
    print("H4 Analysis Stub — Architecture vs Persona Variance Comparison")
    print("Metrics:", METRICS)
    print("Pre-registration timestamp:", __import__("datetime").datetime.utcnow().isoformat())
