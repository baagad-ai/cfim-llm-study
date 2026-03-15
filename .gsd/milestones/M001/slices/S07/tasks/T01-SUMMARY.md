---
id: T01
parent: S07
milestone: M001
provides:
  - docs/osf_preregistration.md — complete pre-registration document (2934 words)
  - src/analysis/h1_self_play_premium.py — H1 Wilcoxon self-play premium stub
  - src/analysis/h2_mixed_effects.py — H2 LRT mixed-effects pairing identity stub
  - src/analysis/h3_identity_disclosure.py — H3 identity disclosure two-part stub
  - src/analysis/h4_adaptation_lag.py — H4 Kruskal-Wallis adaptation lag stub
  - src/analysis/h5_cfim_to_multiagent.py — H5 OLS bilateral-to-multiagent stub
  - data/metadata/osf_registration.json — placeholder pending human OSF submission
  - .gsd/metrics.json — updated with hypotheses_preregistered: true
key_files:
  - docs/osf_preregistration.md
  - src/analysis/h1_self_play_premium.py
  - src/analysis/h2_mixed_effects.py
  - src/analysis/h3_identity_disclosure.py
  - src/analysis/h4_adaptation_lag.py
  - src/analysis/h5_cfim_to_multiagent.py
  - data/metadata/osf_registration.json
key_decisions:
  - D041: H1-H5 analysis stubs replaced from old Harbour design to match CFIM/RNE design
  - D042: H3 uses |M6| (absolute value) not signed — two-sided per Long & Teplica 2025 finding
patterns_established:
  - Pre-registration doc structure: novelty claim → exact H1-H5 statistical statements → analysis plan → data collection plan → metrics → benchmark description → power analysis → exclusion criteria → open science commitments
  - Analysis stubs: module-level docstring with H statement + test specification, load function, compute function, test function, run_hN_analysis entry point
observability_surfaces:
  - data/metadata/osf_registration.json — tracks OSF submission status (PENDING_HUMAN_SUBMISSION until T02)
  - .gsd/metrics.json — hypotheses_preregistered: true, osf_status field
duration: ~1h
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Write Pre-Registration Document and Analysis Stubs

**Pre-registration document (2934 words) and 5 analysis stubs written; old Harbour-design stubs superseded; all stubs import cleanly; metrics.json updated; OSF registration placeholder written pending human submission in T02.**

## What Happened

The dispatched slice was S07 but the authoritative spec was in `S05-PLAN.md` (OSF pre-registration). The S07 directory existed (created by dispatch) but had no plan or task files. Created the plan structure.

The existing analysis stubs (`h1_kruskal_wallis.py`, `h2_logistic_mixed_effects.py`, `h3_commons_exploitation.py`, `h4_architecture_vs_persona.py`) were written for the old Trade Island / Harbour primary study design and are now superseded by the current CFIM/RNE design documented in `SIMULATION_DESIGN.md`. Wrote 5 new stubs that match the pre-registered H1–H5 exactly:

- **H1** (`h1_self_play_premium.py`): Mann-Whitney U on diagonal vs off-diagonal CFIM cell-mean M1 values. Correct test for unequal group sizes (7 diagonal vs 42 off-diagonal cells).
- **H2** (`h2_mixed_effects.py`): Likelihood Ratio Test comparing full model (with pairing identity) vs null model (round effects only). Uses statsmodels `mixedlm` with `reml=False` for LRT validity.
- **H3** (`h3_identity_disclosure.py`): Two-part test. Part A: one-sample t-test that mean |M6| > 0. Part B: Mann-Whitney U that cross-family |M6| > same-family |M6|. Uses absolute value following Long & Teplica (2025) finding that direction is framing-dependent.
- **H4** (`h4_adaptation_lag.py`): Kruskal-Wallis on M3 (adaptation lag) grouped by canonical pairing. Effect size η² > 0.10 required alongside p < 0.05.
- **H5** (`h5_cfim_to_multiagent.py`): OLS regression predicting Study 2 VP variance from mean bilateral M1. R² > 0.15 required.

`docs/osf_preregistration.md` written at 2934 words covering: novelty claim + related work positioning, exact H1–H5 statistical statements with test specs and support criteria, analysis plan with BH correction strategy, data collection plan (3,360 Study 1 sessions, 7 family versions table, perturbation protocol, Phase 0 gates), M1–M7 metric definitions, CFIM benchmark description, power analysis, exclusion criteria, and open science commitments.

## Verification

```
wc -w docs/osf_preregistration.md
→ 2934 words (≥ 1500 required ✓)

python -c "from src.analysis import h1_self_play_premium, h2_mixed_effects, h3_identity_disclosure, h4_adaptation_lag, h5_cfim_to_multiagent; print('All 5 stubs imported successfully.')"
→ All 5 stubs imported successfully. ✓

python -c "import json, pathlib; d = json.loads(pathlib.Path('.gsd/metrics.json').read_text()); print(d['hypotheses_preregistered'])"
→ True ✓

cat data/metadata/osf_registration.json
→ exists with PENDING_HUMAN_SUBMISSION status ✓
```

Slice-level verification: `data/metadata/osf_registration.json` verification check FAILS (osf_registration_url is null) — this is expected for T01. T02 (human OSF submission) is required to pass the final verification check.

## Diagnostics

- `data/metadata/osf_registration.json` — contains `_status: PENDING_HUMAN_SUBMISSION` and full instructions for the human submission step
- `docs/osf_preregistration.md` — the document to upload to OSF
- All 5 new stubs raise `NotImplementedError` or `FileNotFoundError` when called without data — correct stub behavior

## Deviations

- **Stub replacement**: Old stubs (`h1_kruskal_wallis`, `h2_logistic_mixed_effects`, `h3_commons_exploitation`, `h4_architecture_vs_persona`) not deleted — retained in place for git history. New stubs use different filenames matching the current H1–H5 hypothesis names. The old files could be removed before paper submission if desired.
- **S07 vs S05**: Task was dispatched as S07 but canonical plan was in S05-PLAN.md. Created S07-PLAN.md that cross-references S05 and contains the actual task list with T01 marked done.

## Known Issues

- Old analysis stubs (`h1_kruskal_wallis.py` etc.) are still present in `src/analysis/` but implement the wrong design. They should be removed before Phase 1 to avoid confusion. Flagged for cleanup in T02 or a follow-up task.
- OSF registration URL is null until T02 (human submission). The slice-level verification check `assert d.get('osf_registration_url')` will fail until T02 completes.

## Files Created/Modified

- `docs/osf_preregistration.md` — created (2934-word pre-registration document)
- `src/analysis/h1_self_play_premium.py` — created (CFIM H1 stub)
- `src/analysis/h2_mixed_effects.py` — created (CFIM H2 stub)
- `src/analysis/h3_identity_disclosure.py` — created (CFIM H3 stub)
- `src/analysis/h4_adaptation_lag.py` — created (CFIM H4 stub)
- `src/analysis/h5_cfim_to_multiagent.py` — created (CFIM H5 stub)
- `data/metadata/osf_registration.json` — created (placeholder, pending human submission)
- `.gsd/metrics.json` — updated (hypotheses_preregistered: true, analysis_stubs_committed list, osf_status)
- `.gsd/DECISIONS.md` — appended D041, D042
- `.gsd/milestones/M001/slices/S07/S07-PLAN.md` — created (T01 marked done)
- `.gsd/milestones/M001/slices/S07/tasks/T01-PLAN.md` — created
- `.gsd/milestones/M001/slices/S07/tasks/T01-SUMMARY.md` — this file
