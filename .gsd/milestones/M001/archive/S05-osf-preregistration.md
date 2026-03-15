# S05: OSF Pre-Registration + Analysis Stubs

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 3-4 hours
**Requirements:** R010, R009 (stubs)
**Depends on:** Can run in parallel with S02-S04, but must complete before Phase 1

## Goal

OSF account created, H1-H4 hypotheses registered with timestamp lock, analysis scripts committed as executable stubs before any Phase 1 data is collected.

## CRITICAL BLOCKING CONSTRAINT

Phase 1 (M002) cannot start until the OSF formal registration timestamp exists. This proves hypotheses were specified before data collection. If this slice is not complete before Phase 1 games begin, the entire scientific integrity argument collapses.

## Status of Analysis Stubs

Analysis stubs were **already committed** in M001/S01 (2026-03-15, commit c4a9a1d):
- `src/analysis/h1_kruskal_wallis.py` ✅
- `src/analysis/h2_logistic_mixed_effects.py` ✅
- `src/analysis/h3_vp_ratio_ttest.py` ✅
- `src/analysis/h4_architecture_vs_persona.py` ✅
- `src/analysis/heatmap_generator.py` ✅

These are executable stubs with pre-registered test logic and `NotImplementedError` bodies. They will be implemented in M004/S01 once data is collected.

## Tasks

### T01: Create OSF account
- Go to [osf.io](https://osf.io) → create account
- Create new project: **"Pairwise Behavioral Signatures: LLM Family Economic Simulation"**
- Add description (from paper abstract):
  > "A controlled study of how model family shapes multi-agent economic behavior. 6 LLM agents play Trade Island (25-round resource trading, VP victory) across 335 games spanning 4 families: Llama 3.3 70B, DeepSeek V3, Gemini 2.5 Flash, Mistral Small. Primary contribution: first complete pairwise interaction matrix revealing matchup-specific cooperation and exploitation patterns."
- Set visibility to **public** (required for pre-registration legitimacy)

### T02: Write pre-registration document
File: `docs/osf_preregistration.md` (also uploaded to OSF)

Required sections:
1. **Hypotheses** (exact statistical statements):
   - H1: Kruskal-Wallis test on Gini coefficient at round 25 across 4 families, α=0.05
   - H2: Logistic mixed-effects model — accepted ~ pairing_identity + round + round² (random: game_id), LRT p<0.05
   - H3: One-sample t-test on VP ratio per pairing (null: ratio=1.0), BH-corrected, ≥2 of 6 significant
   - H4: Permutation variance comparison (10,000 perms, seed=42) on 5 metrics, arch>persona on ≥3 of 5
2. **Analysis plan**: exact covariates, exclusion criteria, correction methods
3. **Data collection plan**: 335 games, phase structure, model assignments, random seed policy
4. **Preregistered metrics** (for H4): VP at round 25, trade acceptance rate, Gini coefficient, exploitation index, cooperation tendency score
5. **Links**: GitHub repo URL, analysis stub commit hash

### T03: Push analysis stubs to GitHub + link OSF
- Create GitHub repo: `{username}/pairwise-behavioral-signatures`
- Push current state: `git remote add origin <URL> && git push -u origin main`
- Note the commit hash of the analysis stub commit (c4a9a1d or current HEAD)
- Link GitHub repo from OSF project (Settings → Linked Add-ons → GitHub)

### T04: Submit OSF formal pre-registration
- On OSF project → **Registrations** tab → **New registration**
- Template: "Open-Ended Registration" (most flexible for ML research)
- Upload `docs/osf_preregistration.md` as the registration document
- Include GitHub repo link and analysis stub commit hash
- **Submit registration** (this creates the timestamp-locked record — cannot be edited after)
- Note the registration URL and ID

### T05: Update metrics.json
```json
{
  "hypotheses_preregistered": true,
  "osf_registration_id": "<registration_ID>",
  "osf_project_url": "https://osf.io/<project_ID>",
  "osf_registration_url": "https://osf.io/<registration_ID>",
  "github_repo": "https://github.com/{username}/pairwise-behavioral-signatures",
  "preregistration_commit": "c4a9a1d",
  "preregistration_date": "YYYY-MM-DD"
}
```

### T06: Create `docs/` directory and commit
- `mkdir -p docs/`
- Save `docs/osf_preregistration.md` locally
- `git commit -m "M001/S05: OSF pre-registration document + GitHub push"`

## Acceptance Criteria

- [ ] OSF account exists and project is public
- [ ] Pre-registration document written with exact H1-H4 statistical statements
- [ ] OSF formal registration **submitted** (timestamp-locked — not just a file upload)
- [ ] GitHub repo created and linked from OSF
- [ ] `metrics.json` updated with OSF registration ID and URLs
- [ ] `git log` shows analysis stub commit predates any Phase 1 game data

## Notes

- OSF formal registration (not just project creation) is what creates the timestamp-lock
- "Open-Ended Registration" template is fine — no need for AsPredicted or pre-analysis template
- The GitHub commit timestamp (c4a9a1d, 2026-03-15) already establishes that stubs predate data — OSF registration adds a secondary public timestamp
- If OSF review/processing takes >48h: flag as blocker in STATE.md, do not start Phase 1 games
