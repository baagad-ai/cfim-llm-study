#!/usr/bin/env python3
"""generate_calibration_report.py — Phase 0 Calibration Report Generator.

Reads all completed summary.json files from data/phase0/sessions/ and
produces data/phase0/calibration_report.md with:
  1. Parse Rates (per family)
  2. Trade Acceptance / M1 Distribution (per family)
  3. Cost Breakdown
  4. Family-specific Observations
  5. Go/No-Go Decision

Usage:
    python scripts/generate_calibration_report.py
    python scripts/generate_calibration_report.py --data-dir data/phase0/sessions --out data/phase0/calibration_report.md
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timezone

FAMILIES = ["deepseek", "gemini", "llama", "mistral"]
EXPECTED_SESSIONS = 240  # 4 families × 10 reps × 3 conditions × 2 disclosure
ROUNDS_PER_SESSION = 35

# Thresholds (from S03 Must-Haves)
PARSE_RATE_THRESHOLD = 0.90       # ≥90% per family
MIN_ACCEPTED_TRADE_SESSIONS = 1   # ≥1 session with completed_trades>0 per family
BUDGET_USD = 12.00


def load_sessions(data_dir: pathlib.Path) -> list[dict]:
    sessions = []
    for p in sorted(data_dir.glob("*/summary.json")):
        try:
            d = json.loads(p.read_text())
            sessions.append(d)
        except Exception as e:
            print(f"  ⚠  Skipping {p}: {e}", file=sys.stderr)
    return sessions


def compute_parse_rates(sessions: list[dict]) -> dict[str, dict]:
    """Returns per-family: {total_sessions, parse_fail_rounds, parse_rate, passes}"""
    totals = defaultdict(int)
    parse_fails = defaultdict(int)
    for s in sessions:
        fam = s["family_a"]  # monoculture: family_a == family_b
        totals[fam] += 1
        parse_fails[fam] += s.get("parse_failure_count", 0)
    result = {}
    for fam in FAMILIES:
        n = totals.get(fam, 0)
        fails = parse_fails.get(fam, 0)
        denom = n * ROUNDS_PER_SESSION if n > 0 else 1
        rate = 1.0 - fails / denom
        result[fam] = {
            "sessions": n,
            "parse_fail_rounds": fails,
            "parse_rate": rate,
            "passes": rate >= PARSE_RATE_THRESHOLD,
        }
    return result


def compute_trade_acceptance(sessions: list[dict]) -> dict[str, dict]:
    """Returns per-family: {m1_values, mean_m1, min_m1, max_m1, sessions_with_trades, passes}"""
    m1_vals = defaultdict(list)
    trades_count = defaultdict(int)
    for s in sessions:
        fam = s["family_a"]
        m1 = s.get("cooperation_rate", 0.0)
        m1_vals[fam].append(m1)
        if s.get("completed_trades", 0) > 0:
            trades_count[fam] += 1
    result = {}
    for fam in FAMILIES:
        vals = m1_vals.get(fam, [])
        sw = trades_count.get(fam, 0)
        result[fam] = {
            "n": len(vals),
            "mean_m1": statistics.mean(vals) if vals else 0.0,
            "median_m1": statistics.median(vals) if vals else 0.0,
            "min_m1": min(vals) if vals else 0.0,
            "max_m1": max(vals) if vals else 0.0,
            "stdev_m1": statistics.stdev(vals) if len(vals) > 1 else 0.0,
            "sessions_with_trades": sw,
            "passes": sw >= MIN_ACCEPTED_TRADE_SESSIONS,
        }
    return result


def compute_cost(sessions: list[dict]) -> dict:
    total = sum(s.get("total_cost_usd", 0.0) for s in sessions)
    by_family = defaultdict(float)
    by_condition = defaultdict(float)
    by_disclosure = defaultdict(float)
    for s in sessions:
        by_family[s["family_a"]] += s.get("total_cost_usd", 0.0)
        by_condition[s.get("condition", "?")] += s.get("total_cost_usd", 0.0)
        by_disclosure[s.get("disclosure", "?")] += s.get("total_cost_usd", 0.0)
    return {
        "total": total,
        "by_family": dict(sorted(by_family.items())),
        "by_condition": dict(sorted(by_condition.items())),
        "by_disclosure": dict(sorted(by_disclosure.items())),
        "passes_budget": total <= BUDGET_USD,
    }


def compute_per_condition(sessions: list[dict]) -> dict[str, dict[str, dict]]:
    """Per family × condition breakdown of M1 and trades."""
    result: dict[str, dict[str, list]] = {
        fam: {"A": [], "B": [], "C": []} for fam in FAMILIES
    }
    for s in sessions:
        fam = s["family_a"]
        cond = s.get("condition", "?")
        if cond in result.get(fam, {}):
            result[fam][cond].append(s.get("cooperation_rate", 0.0))
    # Summarize
    out = {}
    for fam in FAMILIES:
        out[fam] = {}
        for cond in ["A", "B", "C"]:
            vals = result[fam].get(cond, [])
            out[fam][cond] = {
                "n": len(vals),
                "mean_m1": statistics.mean(vals) if vals else 0.0,
            }
    return out


def make_go_nogo(parse_rates, trade_acceptance, cost) -> tuple[str, list[str], list[str]]:
    """Returns (decision, reasons_pass, reasons_fail)."""
    passes = []
    fails = []

    # Parse rate check
    for fam in FAMILIES:
        pr = parse_rates[fam]
        if pr["sessions"] == 0:
            fails.append(f"Parse rate: {fam} has 0 sessions (incomplete run?)")
        elif pr["passes"]:
            passes.append(f"Parse rate {fam}: {pr['parse_rate']:.1%} ≥ 90% ✓")
        else:
            fails.append(f"Parse rate {fam}: {pr['parse_rate']:.1%} < 90% ✗")

    # Trade acceptance check
    for fam in FAMILIES:
        ta = trade_acceptance[fam]
        if ta["n"] == 0:
            fails.append(f"Trade acceptance: {fam} has 0 sessions (incomplete run?)")
        elif ta["passes"]:
            passes.append(
                f"Trade acceptance {fam}: {ta['sessions_with_trades']}/{ta['n']} sessions have trades ✓"
            )
        else:
            fails.append(
                f"Trade acceptance {fam}: {ta['sessions_with_trades']}/{ta['n']} sessions have trades ✗"
            )

    # Budget check
    if cost["passes_budget"]:
        passes.append(f"Cost: ${cost['total']:.4f} ≤ ${BUDGET_USD:.2f} budget ✓")
    else:
        fails.append(f"Cost: ${cost['total']:.4f} > ${BUDGET_USD:.2f} budget ✗")

    decision = "**GO**" if not fails else "**NO-GO**"
    return decision, passes, fails


def render_report(
    sessions: list[dict],
    parse_rates: dict,
    trade_acceptance: dict,
    cost: dict,
    per_condition: dict,
    decision: str,
    passes: list[str],
    fails: list[str],
    generated_at: str,
) -> str:
    n = len(sessions)
    lines = []
    a = lines.append

    a(f"# Phase 0 Calibration Report")
    a(f"")
    a(f"**Generated:** {generated_at}")
    a(f"**Sessions analysed:** {n} / {EXPECTED_SESSIONS} expected")
    a(f"**Families:** {', '.join(FAMILIES)}")
    a(f"**Design:** 4 monoculture families × 10 replicates × 3 conditions × 2 disclosure = 240 sessions")
    a(f"")

    # ── 1. Parse Rates ──────────────────────────────────────────────
    a(f"---")
    a(f"")
    a(f"## 1. Parse Rates")
    a(f"")
    a(f"Threshold: ≥ 90% per family (parse rate = 1 − parse_fail_rounds / (sessions × {ROUNDS_PER_SESSION} rounds))")
    a(f"")
    a(f"| Family | Sessions | Parse-fail rounds | Parse rate | Pass? |")
    a(f"|--------|----------|-------------------|------------|-------|")
    for fam in FAMILIES:
        pr = parse_rates[fam]
        status = "✓" if pr["passes"] else "✗"
        a(f"| {fam} | {pr['sessions']} | {pr['parse_fail_rounds']} | {pr['parse_rate']:.2%} | {status} |")
    a(f"")

    # ── 2. Trade Acceptance / M1 Distribution ──────────────────────
    a(f"---")
    a(f"")
    a(f"## 2. Trade Acceptance & M1 Distribution")
    a(f"")
    a(f"M1 = cooperation_rate = completed_trades / {ROUNDS_PER_SESSION} rounds per session.")
    a(f"Threshold: ≥ 1 session with completed_trades > 0 per family.")
    a(f"")
    a(f"| Family | N | Mean M1 | Median M1 | Min | Max | Stdev | Sessions w/ trades | Pass? |")
    a(f"|--------|---|---------|-----------|-----|-----|-------|-------------------|-------|")
    for fam in FAMILIES:
        ta = trade_acceptance[fam]
        status = "✓" if ta["passes"] else "✗"
        a(
            f"| {fam} | {ta['n']} | {ta['mean_m1']:.4f} | {ta['median_m1']:.4f} "
            f"| {ta['min_m1']:.4f} | {ta['max_m1']:.4f} | {ta['stdev_m1']:.4f} "
            f"| {ta['sessions_with_trades']}/{ta['n']} | {status} |"
        )
    a(f"")

    # ── 3. Cost Breakdown ──────────────────────────────────────────
    a(f"---")
    a(f"")
    a(f"## 3. Cost Breakdown")
    a(f"")
    a(f"Budget: ≤ ${BUDGET_USD:.2f} total.")
    a(f"")
    a(f"**Total cost: ${cost['total']:.4f}** {'✓ within budget' if cost['passes_budget'] else f'✗ OVER BUDGET (limit ${BUDGET_USD:.2f})'}")
    a(f"")
    a(f"### By family")
    a(f"")
    a(f"| Family | Cost (USD) | Cost per session |")
    a(f"|--------|------------|-----------------|")
    for fam in FAMILIES:
        c = cost["by_family"].get(fam, 0.0)
        n_fam = parse_rates[fam]["sessions"]
        per_s = c / n_fam if n_fam > 0 else 0.0
        a(f"| {fam} | ${c:.4f} | ${per_s:.4f} |")
    a(f"")
    a(f"### By condition")
    a(f"")
    a(f"| Condition | Cost (USD) |")
    a(f"|-----------|------------|")
    for cond in sorted(cost["by_condition"]):
        a(f"| {cond} | ${cost['by_condition'][cond]:.4f} |")
    a(f"")
    a(f"### By disclosure")
    a(f"")
    a(f"| Disclosure | Cost (USD) |")
    a(f"|------------|------------|")
    for disc in sorted(cost["by_disclosure"]):
        a(f"| {disc} | ${cost['by_disclosure'][disc]:.4f} |")
    a(f"")

    # ── 4. Family-specific Observations ───────────────────────────
    a(f"---")
    a(f"")
    a(f"## 4. Family-specific Observations")
    a(f"")
    a(f"M1 by family × condition (mean cooperation rate per condition cell):")
    a(f"")
    a(f"| Family | Cond A (n) | Mean M1 | Cond B (n) | Mean M1 | Cond C (n) | Mean M1 |")
    a(f"|--------|-----------|---------|-----------|---------|-----------|---------|")
    for fam in FAMILIES:
        row = per_condition[fam]
        a(
            f"| {fam} "
            f"| {row['A']['n']} | {row['A']['mean_m1']:.4f} "
            f"| {row['B']['n']} | {row['B']['mean_m1']:.4f} "
            f"| {row['C']['n']} | {row['C']['mean_m1']:.4f} |"
        )
    a(f"")
    a(f"### Observations")
    a(f"")
    for fam in FAMILIES:
        ta = trade_acceptance[fam]
        pr = parse_rates[fam]
        cost_fam = cost["by_family"].get(fam, 0.0)
        n_fam = pr["sessions"]
        per_s = cost_fam / n_fam if n_fam > 0 else 0.0
        a(f"**{fam}** ({n_fam} sessions, ${per_s:.4f}/session)")
        if n_fam == 0:
            a(f"- No sessions completed.")
        else:
            a(f"- Parse rate: {pr['parse_rate']:.1%} ({pr['parse_fail_rounds']} fail rounds across {n_fam * ROUNDS_PER_SESSION} total)")
            a(f"- Mean M1: {ta['mean_m1']:.4f}, sessions with ≥1 trade: {ta['sessions_with_trades']}/{n_fam}")
            # Flag zero-trade families
            if ta["sessions_with_trades"] == 0:
                a(f"- ⚠  Zero trade sessions — may need prompt tuning before Phase 1")
            if pr["parse_rate"] < 0.95:
                a(f"- ⚠  Parse rate below 95% — review JSON output format")
        a(f"")

    # ── 5. Go/No-Go Decision ───────────────────────────────────────
    a(f"---")
    a(f"")
    a(f"## 5. Go/No-Go Decision")
    a(f"")
    a(f"### Decision: {decision}")
    a(f"")
    if passes:
        a(f"**Criteria met:**")
        for p in passes:
            a(f"- {p}")
        a(f"")
    if fails:
        a(f"**Criteria failed:**")
        for f_ in fails:
            a(f"- {f_}")
        a(f"")

    if decision == "**GO**":
        a(f"All Go/No-Go criteria are met. Phase 1 (Study 1 full CFIM pairwise run) may proceed.")
        a(f"")
        a(f"> **Recommendation:** Proceed to M002 Phase 1. Review family-specific M1 distributions")
        a(f"> above to set Phase 1 baseline expectations for each family pair.")
    else:
        a(f"One or more Go/No-Go criteria are not met. Review failures above before proceeding to Phase 1.")
        a(f"")
        a(f"> **Recommendation:** Address failed criteria, then re-run affected families with `--resume --family <name>`")
        a(f"> and regenerate this report.")

    a(f"")
    a(f"---")
    a(f"")
    a(f"*Report generated by `scripts/generate_calibration_report.py`*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate Phase 0 calibration report.")
    parser.add_argument(
        "--data-dir",
        default="data/phase0/sessions",
        help="Directory containing session subdirs (default: data/phase0/sessions)",
    )
    parser.add_argument(
        "--out",
        default="data/phase0/calibration_report.md",
        help="Output report path (default: data/phase0/calibration_report.md)",
    )
    args = parser.parse_args()

    data_dir = pathlib.Path(args.data_dir)
    out_path = pathlib.Path(args.out)

    print(f"Loading sessions from {data_dir}...", file=sys.stderr)
    sessions = load_sessions(data_dir)
    print(f"  → {len(sessions)} sessions loaded", file=sys.stderr)

    if len(sessions) == 0:
        print("ERROR: No sessions found. Run scripts/run_phase0.py first.", file=sys.stderr)
        sys.exit(1)

    if len(sessions) < EXPECTED_SESSIONS:
        print(
            f"  ⚠  Only {len(sessions)}/{EXPECTED_SESSIONS} sessions complete. "
            f"Report will reflect partial data.",
            file=sys.stderr,
        )

    parse_rates = compute_parse_rates(sessions)
    trade_acceptance = compute_trade_acceptance(sessions)
    cost = compute_cost(sessions)
    per_condition = compute_per_condition(sessions)
    decision, passes, fails = make_go_nogo(parse_rates, trade_acceptance, cost)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    report = render_report(
        sessions, parse_rates, trade_acceptance, cost, per_condition,
        decision, passes, fails, generated_at
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)
    print(f"  → Report written to {out_path}", file=sys.stderr)

    # Print summary to stdout
    print(f"\nPhase 0 Summary ({len(sessions)}/{EXPECTED_SESSIONS} sessions):")
    print(f"  Decision: {decision}")
    for fam in FAMILIES:
        pr = parse_rates[fam]
        ta = trade_acceptance[fam]
        print(
            f"  {fam}: parse={pr['parse_rate']:.1%} trades={ta['sessions_with_trades']}/{ta['n']}"
        )
    print(f"  Total cost: ${cost['total']:.4f} / ${BUDGET_USD:.2f}")

    return 0 if decision == "**GO**" else 1


if __name__ == "__main__":
    sys.exit(main())
