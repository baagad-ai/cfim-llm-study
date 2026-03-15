"""
PRE-REGISTERED ANALYSIS STUB — H2: Pairing Identity Predicts Cooperation
=========================================================================
Study: Cross-Family Interaction Matrix (CFIM)
Game: Repeated Negotiated Exchange (RNE), 35 rounds
Pre-registered: 2026-03-15 (this commit predates Phase 1 data collection)
DO NOT modify the statistical test after Phase 1 data collection begins.

H2 — Pairing Identity Predicts Cooperation:
  A mixed-effects logistic model has significantly better fit than a null
  model that includes only round effects.

  Full model:
    trade_completed ~ family_a * family_b + round + round^2
                    + condition + (1 | session_id)

  Null model:
    trade_completed ~ round + round^2 + condition + (1 | session_id)

  Test: Likelihood Ratio Test (LRT), chi-squared, p < 0.05
  Interpretation: If supported, opponent identity (which specific family pair
  is playing) significantly predicts trade completion beyond round dynamics.
  This establishes that the CFIM matrix carries real signal.

Expected JSONL schema fields (from study1/{session_id}/game.jsonl):
  session_id, family_a, family_b, condition, disclosure, prompt_framing,
  round (int 1–35), agent_id, action (propose|accept|reject|pass),
  trade_completed (bool, round-level outcome)
"""

from pathlib import Path
import json

import polars as pl
import numpy as np


def load_study1_round_data(data_dir: Path = Path("data/study1")) -> pl.DataFrame:
    """
    Load per-round trade outcome data from Study 1 game.jsonl files.

    Returns DataFrame with one row per round per session:
      session_id, family_a, family_b, condition, disclosure, prompt_framing,
      round, trade_completed (int 0/1)
    """
    rows = []
    for session_dir in sorted(data_dir.iterdir()):
        if not session_dir.is_dir():
            continue
        meta_path = session_dir / "metadata.json"
        game_path = session_dir / "game.jsonl"
        if not (meta_path.exists() and game_path.exists()):
            continue
        try:
            meta = json.loads(meta_path.read_text())
            for line in game_path.read_text().splitlines():
                if not line.strip():
                    continue
                event = json.loads(line)
                if event.get("event") == "round_end":
                    rows.append({
                        "session_id": meta["session_id"],
                        "family_a": meta["family_a"],
                        "family_b": meta["family_b"],
                        "condition": meta["condition"],
                        "disclosure": meta["disclosure"],
                        "prompt_framing": meta["prompt_framing"],
                        "round": event["round"],
                        "trade_completed": int(event.get("trade_completed", 0)),
                    })
        except Exception as e:
            print(f"WARNING: skipping {session_dir.name}: {e}")

    if not rows:
        raise FileNotFoundError(
            f"No game.jsonl files found under {data_dir}. "
            "Run Study 1 data collection before running analysis."
        )
    df = pl.DataFrame(rows)
    df = df.with_columns([
        pl.col("round").cast(pl.Int32),
        (pl.col("round") ** 2).cast(pl.Float64).alias("round_sq"),
    ])
    return df


def fit_mixed_effects_models(df: pl.DataFrame) -> dict:
    """
    Fit full and null mixed-effects logistic models.

    Uses statsmodels MixedLM with a logistic link (via formula interface).
    Note: statsmodels mixed-effects logistic regression uses Laplace approximation.

    Returns dict with lrt_statistic, lrt_df, lrt_p_value, full_aic, null_aic,
    full_bic, null_bic, and raw model objects.
    """
    try:
        import statsmodels.formula.api as smf
    except ImportError:
        raise ImportError(
            "statsmodels is required for H2 analysis. "
            "Install with: pip install statsmodels"
        )

    pdf = df.to_pandas()

    # Encode pairing as single categorical variable (family_a:family_b)
    pdf["pairing"] = pdf["family_a"] + ":" + pdf["family_b"]

    null_formula = "trade_completed ~ round + round_sq + C(condition)"
    full_formula = (
        "trade_completed ~ C(pairing) + round + round_sq + C(condition)"
    )

    # Mixed-effects logistic regression with random intercept per session
    null_model = smf.mixedlm(
        null_formula, pdf, groups=pdf["session_id"]
    ).fit(reml=False, disp=False)

    full_model = smf.mixedlm(
        full_formula, pdf, groups=pdf["session_id"]
    ).fit(reml=False, disp=False)

    # LRT: chi-squared with df = difference in parameters
    lrt_stat = -2 * (null_model.llf - full_model.llf)
    lrt_df = full_model.df_modelwc - null_model.df_modelwc
    from scipy import stats
    lrt_p = float(stats.chi2.sf(lrt_stat, df=max(lrt_df, 1)))

    return {
        "lrt_statistic": float(lrt_stat),
        "lrt_df": int(lrt_df),
        "lrt_p_value": lrt_p,
        "full_aic": float(full_model.aic),
        "null_aic": float(null_model.aic),
        "full_bic": float(full_model.bic),
        "null_bic": float(null_model.bic),
        "full_llf": float(full_model.llf),
        "null_llf": float(null_model.llf),
        "full_model": full_model,
        "null_model": null_model,
    }


def test_h2(df: pl.DataFrame) -> dict:
    """
    PRE-REGISTERED TEST: H2 — Pairing Identity Predicts Cooperation

    Args:
        df: Study 1 round-level DataFrame in expected schema

    Returns dict with keys:
        lrt_statistic, lrt_df, lrt_p_value, full_aic, null_aic,
        delta_aic (null - full, positive = full is better),
        supported (bool, p < 0.05), narrative (str)
    """
    results = fit_mixed_effects_models(df)

    supported = results["lrt_p_value"] < 0.05
    delta_aic = results["null_aic"] - results["full_aic"]

    narrative = (
        f"H2 {'SUPPORTED' if supported else 'NOT SUPPORTED'}: "
        f"LRT chi2({results['lrt_df']})={results['lrt_statistic']:.2f}, "
        f"p={results['lrt_p_value']:.4f}; "
        f"delta_AIC(null-full)={delta_aic:.1f} "
        f"({'full model better' if delta_aic > 0 else 'null model better or equivalent'})"
    )

    return {
        "hypothesis": "H2",
        "lrt_statistic": results["lrt_statistic"],
        "lrt_df": results["lrt_df"],
        "lrt_p_value": results["lrt_p_value"],
        "full_aic": results["full_aic"],
        "null_aic": results["null_aic"],
        "delta_aic": delta_aic,
        "supported": supported,
        "narrative": narrative,
    }


def run_h2_analysis(data_dir: Path = Path("data/study1")) -> dict:
    """Entry point: load round data, run H2 test, return results dict."""
    df = load_study1_round_data(data_dir)
    return test_h2(df)
