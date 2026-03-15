# S05: OSF Pre-Registration + Analysis Stubs

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 3-4 hours
**Requirements:** R010, R009 (stubs)

## Goal

OSF account created, H1-H4 hypotheses registered with timestamp lock, analysis scripts committed as executable stubs before any Phase 1 data is collected.

## Tasks

### T01: Create OSF account
- Go to osf.io → create account
- Create project: "Pairwise Behavioral Signatures: LLM Family Economic Simulation"
- Add description from paper abstract
- Record OSF project URL in metrics.json

### T02: Write pre-registration document
- Hypotheses (exact statistical statements):
  - H1: Gini coefficient at round 25 differs across 4 families (Kruskal-Wallis, α=0.05)
  - H2: Cross-model trade acceptance rate depends on pairing identity (logistic mixed-effects, game as random effect)
  - H3: VP ratio deviates from 1.0 for ≥2 of 6 pairwise conditions (one-sample t-test, BH-corrected)
  - H4: Architecture variance > persona variance on ≥3 of 5 metrics (permutation-based variance comparison)
- Analysis plan: describe exact statistical tests, covariates, exclusion criteria
- Data collection plan: 335 games, phase structure, model assignments
- Upload to OSF as pre-registration (not just a file — use OSF's formal registration feature)

### T03: Implement analysis stub scripts
- `src/analysis/h1_kruskal_wallis.py` — stub: loads dataframe, runs KW test, prints result
- `src/analysis/h2_logistic_mixed_effects.py` — stub: loads dataframe, fits model, prints coefficients
- `src/analysis/h3_vp_ratio_ttest.py` — stub: loads dataframe, runs t-tests with BH correction
- `src/analysis/h4_architecture_vs_persona.py` — stub: loads dataframe, runs permutation variance comparison
- `src/analysis/behavioral_classifier.py` — stub: three-track classifier (behavior/language/meta-behavioral)
- `src/analysis/heatmap_generator.py` — stub: generates 4×4 pairwise heatmaps
- Each stub: reads a fixed input schema, has TODO comments for implementation, but RUNS without error on empty/mock data

### T04: Commit stubs to git + link to OSF
- `git commit -m "pre-registration: analysis stubs for H1-H4"` with timestamp
- Push to GitHub (create repo if needed): `prajwalmishra/pairwise-behavioral-signatures`
- Link GitHub repo from OSF project
- Formally register the OSF pre-registration (this creates the timestamp-locked record)
- Record OSF registration ID in `metrics.json` → `osf_registration_id`

### T05: Update metrics.json
- `"hypotheses_preregistered": true`
- `"osf_registration_id": "<ID>"`
- `"osf_project_url": "<URL>"`
- `"github_repo": "<URL>"`

## Acceptance Criteria

- [ ] OSF account exists, project created
- [ ] Pre-registration document written with exact H1-H4 statistical statements
- [ ] OSF formal registration submitted (timestamp-locked)
- [ ] All 4 analysis stub scripts exist and run without error
- [ ] Stubs committed to git BEFORE any Phase 1 game data exists
- [ ] `metrics.json` updated with OSF registration ID
- [ ] GitHub repo created and linked from OSF

## CRITICAL: This slice is a hard blocker on M002

Phase 1 cannot start until OSF registration is confirmed (we need the timestamp to show pre-registration predates data collection). If OSF process takes >1 day, flag as blocker in STATE.md.

## Notes

- OSF pre-registration is free
- The formal registration feature locks the document with a timestamp — this is what matters for reviewers
- Analysis stubs just need to be executable Python files that define the analysis plan, even if they use mock data
- Future work: update stubs with actual implementation in M004/S01
