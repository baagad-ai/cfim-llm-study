# T01: Write Pre-Registration Document and Analysis Stubs

**Slice:** S07 (OSF Pre-Registration — maps to S05-PLAN.md authoritative spec)
**Milestone:** M001

## Goal

Write `docs/osf_preregistration.md` (full pre-registration document for CFIM study) and replace legacy analysis stubs H1–H4 + create new H5 stub, all matching the current CFIM/RNE design from SIMULATION_DESIGN.md. Commit everything before Phase 1 begins.

## Steps

- [ ] **T01-1** Write `src/analysis/h1_self_play_premium.py` — Wilcoxon signed-rank diagonal vs off-diagonal
- [ ] **T01-2** Write `src/analysis/h2_mixed_effects.py` — LRT mixed-effects logistic regression
- [ ] **T01-3** Write `src/analysis/h3_identity_disclosure.py` — identity sensitivity t-test + Wilcoxon
- [ ] **T01-4** Write `src/analysis/h4_adaptation_lag.py` — Kruskal-Wallis on adaptation lag per pairing
- [ ] **T01-5** Write `src/analysis/h5_cfim_to_multiagent.py` — bilateral CFIM predicts Harbour VP variance
- [ ] **T01-6** Write `docs/osf_preregistration.md` — full pre-reg document (≥1500 words)
- [ ] **T01-7** Write `data/metadata/osf_registration.json` — placeholder pending human submission
- [ ] **T01-8** Verify all stubs importable, doc ≥ 1500 words

## Must-Haves

- All 5 analysis stubs importable with no errors
- `docs/osf_preregistration.md` ≥ 1500 words with exact H1–H5 statistical statements
- `data/metadata/osf_registration.json` written (may have null registration_url pending human action)
- `metrics.json` updated with `hypotheses_preregistered: true`

## est: 2h
