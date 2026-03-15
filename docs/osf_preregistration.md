# OSF Pre-Registration: Cross-Family Interaction Matrix (CFIM)
## Opponent-Contingent Behavioral Profiles in LLM Agents

**Study title:** Cross-Family Interaction Matrix: How LLM Behavioral Profiles Shift as a Function of Opponent Model Family

**Submitted to:** Open Science Framework (OSF) — Registrations

**Registration date:** 2026-03-15 (prior to Phase 1 data collection)

**GitHub repository:** https://github.com/[to-be-added]/cfim-study

**Primary analysis stub commit:** [to-be-added — commit hash of this file's first commit]

**Target venue:** AAMAS 2027, GAAI track (full paper); backup NeurIPS 2026 Foundation Models workshop

---

## 1. Research Question and Novelty Claim

### 1.1 The Core Question

Do LLM cooperation profiles constitute fixed behavioral traits, or are they opponent-contingent responses that vary based on which model family the agent is paired against?

Prior work (Akata et al., 2025, *Nature Human Behaviour*; GAMA-Bench 2024; "AI in the Mirror," arXiv:2508.18467, 2025) has measured LLM behavior in multi-agent settings but has not tested whether a model's *strategy itself* changes as a function of which opponent family it faces, while holding the game structure constant.

This study fills that gap by constructing the first **Cross-Family Interaction Matrix (CFIM)**: a 7×7 behavioral matrix measuring cooperation rates, exploitation deltas, and adaptation dynamics for every unique pairwise combination of major LLM families in a controlled repeated-game environment.

### 1.2 Novelty Relative to Prior Work

| Prior work | What they did | Gap this study fills |
|---|---|---|
| Akata et al. 2025 (NHB) | Cross-family PD games; aggregate heatmaps | Did not analyze opponent-contingency or identity disclosure effects |
| "AI in the Mirror" 2025 | Self vs. non-self disclosure in Public Goods Game | Cross-family label disclosure; 7 families; 3 game conditions; RNE mechanics |
| GAMA-Bench 2024 | Strategic reasoning performance across 13 LLMs | Behavioral adaptation and relational profiles, not performance benchmarking |
| NetworkGames 2025 | 16×16 personality dyadic matrix | Model families as natural groupings; game-theoretic structure; safety implications |

### 1.3 Why This Matters

- **AI Safety:** Models that cooperate in same-family self-play may exploit cross-family opponents. Single-family evaluation is insufficient for deployment safety assessment.
- **Multi-agent system design:** Emergent behavior in mixed-family systems cannot be predicted from single-family benchmarks alone.
- **Evaluation infrastructure:** CFIM is a reusable benchmark — new model families can be added to the matrix without repeating prior comparisons.

---

## 2. Hypotheses — Exact Statistical Statements

All five hypotheses are pre-registered before any Phase 1 data collection. The analysis stubs implementing these exact tests are committed at the same timestamp in `src/analysis/`.

### H1 — Self-Play Premium

**Claim:** Cooperation rates on the CFIM diagonal (same-family pairs) are significantly higher than off-diagonal cells (cross-family pairs).

**Operationalization:**
- Unit of analysis: cell-level mean M1 (cooperation rate), where each cell is defined by (family_a × family_b × condition × disclosure)
- Diagonal cells: family_a == family_b (7 cells)
- Off-diagonal cells: family_a ≠ family_b (up to 42 cells from upper triangle × 2 disclosure conditions)
- Cell mean M1 = mean(M1_cooperation_rate) across all sessions in that cell (20 runs × 3 framings = up to 60 sessions per cell)

**Statistical test:** Mann-Whitney U test (Wilcoxon rank-sum), one-sided alternative: diagonal > off-diagonal.

**Significance threshold:** p < 0.05 (one-sided)

**Effect size reported:** r = Z / sqrt(N), where Z is the normal approximation of U and N = n_diagonal + n_offdiagonal.

**Support criterion:** p < 0.05 AND median(diagonal) > median(off-diagonal).

**Implementation:** `src/analysis/h1_self_play_premium.py::test_h1()`

---

### H2 — Pairing Identity Predicts Cooperation

**Claim:** A mixed-effects logistic model including pairing identity has significantly better fit than a null model with only round effects.

**Full model:**
```
trade_completed ~ C(pairing) + round + round^2 + C(condition) + (1 | session_id)
```
where `pairing` = concatenation of sorted(family_a, family_b), encoding the specific family combination.

**Null model:**
```
trade_completed ~ round + round^2 + C(condition) + (1 | session_id)
```

**Unit of analysis:** Round-level trade outcome (trade_completed = 0/1), one row per round per session.

**Statistical test:** Likelihood Ratio Test (LRT), chi-squared distributed, degrees of freedom = difference in parameter count between full and null model.

**Significance threshold:** LRT p < 0.05

**Effect size reported:** ΔAIC (null AIC − full AIC); positive value = full model is better.

**Support criterion:** LRT p < 0.05.

**Implementation:** `src/analysis/h2_mixed_effects.py::test_h2()`

---

### H3 — Identity Disclosure Amplifies Behavioral Divergence

**Claim (two parts, both required):**

- **Part A:** Mean |M6| (absolute identity sensitivity) > 0 across all session pairs, indicating that opponent family disclosure changes behavior on average.
- **Part B:** Cell-level |M6| is larger for cross-family pairs than same-family pairs.

**M6 definition:** M6 = |M1_disclosed − M1_blind| for matched session pairs sharing the same (family_a, family_b, condition, prompt_framing, random_seed) with disclosure varying (blind vs. disclosed).

**NOTE on direction:** M6 is defined as the absolute value. The direction of the disclosure effect is NOT pre-specified, consistent with evidence from Long & Teplica (2025) showing that disclosure can increase OR decrease cooperation depending on framing.

**Part A test:** One-sample t-test, H0: mean(|M6|) = 0, one-sided alternative: mean > 0. Significance threshold: p < 0.05.

**Part B test:** Mann-Whitney U test on cell-level mean |M6| values, one-sided alternative: cross-family > same-family. Significance threshold: p < 0.05.

**Support criterion:** Both Part A AND Part B must show p < 0.05 with the predicted direction.

**Implementation:** `src/analysis/h3_identity_disclosure.py::test_h3()`

---

### H4 — Adaptation Lag Differs by Family Pair

**Claim:** M3 (adaptation lag in rounds after perturbation at round 20) varies significantly across the 28 unique canonical pairings.

**M3 definition:** Number of rounds after round 20 until the focal agent's trade proposal rate changes by ≥ 0.30 absolute change from its rounds-1-to-19 baseline, sustained for ≥ 3 consecutive rounds. M3 = null if the agent never adapts within the 15 post-perturbation rounds (rounds 21–35).

**Canonical pairing:** sorted(family_a, family_b) concatenated with underscore — de-duplicates A×B = B×A. 7 families → 28 unique canonical pairings (C(7,2) + 7 diagonal).

**Statistical test:** Kruskal-Wallis test across all canonical pairings with ≥ 3 valid (non-null) M3 observations.

**Significance threshold:** p < 0.05

**Effect size:** η² = (H − k + 1) / (n − k), where H = Kruskal-Wallis statistic, k = number of groups, n = total valid observations.

**Pre-specified effect size threshold:** η² > 0.10

**Support criterion:** p < 0.05 AND η² > 0.10. Both must hold.

**Null handling:** Sessions where M3 = null are excluded from the test. Null rate per pairing is reported as a secondary diagnostic.

**Implementation:** `src/analysis/h4_adaptation_lag.py::test_h4()`

---

### H5 — CFIM Patterns Predict Multi-Agent Outcomes

**Claim:** In Study 2 mixed-composition Harbour games (6-agent resource game, 30 rounds), the mean bilateral cooperation rate from Study 1 for the specific family pairs present in the game predicts final VP variance across agents.

**Predictor construction:** For each Study 2 game with agent family composition F = [f₁, f₂, ..., f₆], compute: `mean_bilateral_M1 = mean over all unique pairs (fᵢ, fⱼ) with i < j of CFIM[fᵢ, fⱼ]`, where CFIM values are Study 1 blind-condition cell means.

**Outcome variable:** `vp_variance` = variance of final VP scores across agents at end of Harbour game.

**Statistical test:** OLS linear regression: `vp_variance ~ mean_bilateral_M1`

**Significance thresholds:**
- p < 0.05 for the predictor coefficient
- R² > 0.15

**Support criterion:** Both p < 0.05 AND R² > 0.15 must hold.

**Implementation:** `src/analysis/h5_cfim_to_multiagent.py::test_h5()`

---

## 3. Analysis Plan

### 3.1 Primary Analysis Pipeline

1. **Data validation:** Check JSONL schema completeness, flag and exclude sessions with >10% missing rounds or cost >$0.10 (single-session cost anomaly threshold). Log exclusions.
2. **H1:** Compute cell-level mean M1; run Mann-Whitney U; report r effect size. Visualize via CFIM heatmap (8×8 grid, color = M1, diagonal highlighted).
3. **H2:** Load round-level events; fit null and full mixed-effects models; run LRT; report ΔAIC and pairing-specific odds ratios.
4. **H3:** Match blind/disclosed session pairs by seed; compute |M6| per pair; run Part A one-sample t-test and Part B Mann-Whitney U; report matched pair count and unmatched rate.
5. **H4:** Group M3 values by canonical pairing; run Kruskal-Wallis; report η²; plot adaptation lag distributions per pairing as violin plots.
6. **H5:** Load Study 2 summaries; compute mean_bilateral_M1 per game; run OLS; report R², β, and scatter plot with regression line.

### 3.2 Multiple Comparison Correction

H1–H4 are four independent tests on Study 1 data. We apply Benjamini-Hochberg (BH) correction across these four p-values and report both raw and adjusted p-values. H5 is a separate test on Study 2 data and is not included in the BH correction family (different dataset).

### 3.3 Covariates and Moderators

All primary models include `condition` (A/B/C) and `prompt_framing` (neutral/social/strategic) as fixed effects. Sensitivity analyses will test:
- Models restricted to Condition A only (pure coordination — cleanest M1 signal)
- Models with `round` × `condition` interaction
- Excluding sessions where JSON parse failure rate exceeded 5%

### 3.4 Effect Size Thresholds (Pre-Specified)

| Hypothesis | Effect size metric | Pre-registered threshold |
|---|---|---|
| H1 | r (Mann-Whitney) | Not pre-specified — report and interpret |
| H2 | ΔAIC | Not pre-specified — report direction |
| H3 | Cohen's d for Part A | Not pre-specified — report and interpret |
| H4 | η² (Kruskal-Wallis) | η² > 0.10 required for support |
| H5 | R² (OLS) | R² > 0.15 required for support |

### 3.5 Visualizations (Pre-Specified)

1. **Figure 1:** 7×7 CFIM heatmap (M1 cooperation rate, blind condition). Diagonal cells highlighted with a bold border. Implemented in `src/analysis/heatmap_generator.py`.
2. **Figure 2:** Disclosure delta matrix — signed M6 per cell, diverging colormap (red = disclosure decreases cooperation, blue = disclosure increases).
3. **Figure 3:** Adaptation lag violin plots by canonical pairing (H4).
4. **Figure 4:** H5 scatter plot — mean_bilateral_M1 (x) vs. Harbour VP variance (y) with OLS regression line and 95% CI band.

---

## 4. Data Collection Plan

### 4.1 Study 1: CFIM (Primary)

**Game:** Repeated Negotiated Exchange (RNE), 35 rounds per session, perturbation at round 20.

**Design factors (fully crossed):**
- Family A × Family B: 7 × 7 = 49 cells (including diagonal same-family); collapsed to 28 canonical unique pairings
- Condition: A (coordination/Stag Hunt), B (mixed motive/PD), C (asymmetric power/Ultimatum)
- Disclosure: blind, disclosed
- Prompt framing: neutral, social, strategic

**Sessions per cell:** 20 runs per canonical pairing × condition × disclosure (3 framings distributed across the 20 runs, ~7 per framing).

**Total Study 1 sessions:** 28 canonical pairings × 3 conditions × 2 disclosure × 20 runs = 3,360 sessions.

**Estimated cost:** $47 at mean $0.014/session.

### 4.2 Study 2: Harbour (Ecological Validity)

**Game:** 6-agent Harbour resource-management game, 30 rounds.

**Compositions tested:**
- Monoculture: all 6 agents from same family — 7 families × 20 games = 140 games
- Mixed: compositions designed from Study 1 CFIM findings — approximately 60 games across 10–12 designed compositions (exact compositions specified after Study 1 completes)

**Total Study 2 sessions:** ~200 games.

**Estimated cost:** $15.

### 4.3 Model Family Pool (Exact Versions)

| Family ID | Model string | Provider | Route |
|---|---|---|---|
| llama | Llama 3.3 70B | Groq | `groq/llama-3.3-70b-versatile` |
| deepseek | DeepSeek V3 | OpenRouter | `openrouter/deepseek/deepseek-chat` |
| gemini | Gemini 2.5 Flash | Google AI Studio | `gemini/gemini-2.5-flash` |
| mistral | Mistral Small 2506 | Mistral | `mistral/mistral-small-2506` |
| gpt4o | GPT-4o mini | OpenAI | `openai/gpt-4o-mini` |
| qwen | Qwen 2.5 72B | Together.ai | `together/qwen/qwen-2.5-72b-instruct` |
| phi | Phi-4 | Together.ai | `together/microsoft/phi-4` |

**Note:** Claude 3.5 Haiku was excluded to keep total budget ≤ $80 (Anthropic pricing pushes Study 1 to $87+ if included). Claude can be added in an extension study. GPT-4o-mini represents the OpenAI family at 17× lower cost than GPT-4o with similar behavioral profiles in prior benchmarks.

### 4.4 Perturbation Protocol (Study 1)

At round 20 of every 35-round session, the opponent's strategy switches (scripted, not the other LLM). Cooperative-baseline sessions: opponent switches to consistent defection (reject all offers, propose zero trades). Defective-baseline sessions: opponent switches to consistent cooperation. The perturbation type is balanced across the 20 runs per cell.

**Adaptation lag window:** Rounds 21–35 (15 rounds post-perturbation).

### 4.5 Data Quality Gates (Phase 0)

Before Phase 1 begins, Phase 0 calibration (120 sessions, 4 core families) must pass 5 gates:
1. Disclosure effect detected in RNE (≥ 5% absolute change on M1 in disclosed vs. blind)
2. Adaptation detected in ≥ 70% of sessions post-perturbation
3. Decay rate (10%) produces trade in ≥ 60% of rounds (urgency confirmed)
4. All 7 model families route correctly (JSONL `model_family` field verified)
5. Phase 0 cost ≤ $15

**If any gate fails:** Design parameters are adjusted (fallback values specified in SIMULATION_DESIGN.md) before Phase 1 begins.

---

## 5. Pre-Specified Metrics M1–M7

### Study 1 Metrics (per session)

**M1: Cooperation Rate** — `trades_completed / max_possible_trades` across all 35 rounds. A completed trade requires both agents to have proposed compatible offers or one agent to have accepted the other's proposal.

**M2: Exploitation Delta** — Signed resource value advantage accumulated by the focal agent from completed trades. Positive = focal agent gained more value than the opponent. Computed as: `sum over completed trades of (focal_agent_value_gain − opponent_value_gain)`.

**M3: Adaptation Lag** — Rounds after perturbation (round 20) until the focal agent's trade proposal rate changes by ≥ 0.30 absolute from baseline (rounds 1–19 mean), sustained ≥ 3 consecutive rounds. Null if never adapted.

**M4: Betrayal Recovery** — Rounds to return to pre-betrayal cooperation rate (baseline M1 ± 0.15) after the perturbation, for sessions where the perturbation was a switch to defection. Null if cooperation rate never recovered.

**M5: Minimum Acceptable Offer** — In Condition C (Ultimatum structure), the lowest fraction of total surplus the focal agent accepts when playing as responder. Elicited from the scripted offer sweep in rounds 25–35. Null for Condition A and B sessions.

**M6: Identity Sensitivity** — `|M1_disclosed − M1_blind|` for matched session pairs. Computed during H3 analysis; not stored directly in session summary files (derived metric).

**M7: Prompt Framing Sensitivity** — Coefficient of variation of M1 across the three prompt framings (neutral, social, strategic) within a cell. High M7 = the cell's cooperation rate is unstable across framings. Reported as a secondary metric; not a primary hypothesis.

---

## 6. CFIM Benchmark Description

The Cross-Family Interaction Matrix (CFIM) is released as a reusable benchmark artifact. It consists of:

- **The matrix itself:** An N×N table where each cell (family_a, family_b) reports mean M1, M2, M3, M4, M6 across all runs, conditions, and disclosure modes, along with 95% confidence intervals.
- **Per-condition sub-matrices:** Separate matrices for Condition A, B, and C.
- **Per-disclosure sub-matrices:** Separate matrices for blind and disclosed sub-conditions.
- **New model placement protocol:** Any new LLM family can be added to the matrix by running 20 sessions against each existing family (28 new sessions total for a 7-family matrix), using the same game parameters. The matrix rows/columns for the new family are filled; existing rows/columns remain valid.

The CFIM benchmark is designed for reproducibility: game parameters, prompts, model versions, and analysis code are fully specified and committed. Results are expected to shift when model versions change (the matrix captures a snapshot of LLM behaviors as of the model versions tested); this is a feature, not a limitation — version-dated matrices track behavioral change over time.

---

## 7. Statistical Power and Sample Size Justification

**Minimum detectable effect (Study 1, H1):**

With 7 diagonal cells and 42 off-diagonal cells, a Mann-Whitney U test (one-sided, α = 0.05, power = 0.80) requires a medium effect size (r ≈ 0.35). From Long & Teplica (2025), disclosure-induced cooperation changes are 11–42% of range; our effect is across-family identity, expected to be ≥ 8.1% based on the "AI in the Mirror" data. The design detects Δ ≥ 8.1% absolute cooperation rate difference.

**N=20 sessions per cell justification:** Based on observed cooperation rate variance from Phase 0 calibration. With σ ≈ 0.20 (cooperation rate std), n=20 provides 80% power to detect Δ = 0.13 (one-tailed t-test, α = 0.05). Smaller per-cell n would reduce power below acceptable levels.

**Study 2 power (H5):** 60 mixed-composition games provides 80% power for OLS regression R² > 0.15 (equivalent to r > 0.39) at α = 0.05.

---

## 8. Exclusion Criteria

Sessions will be excluded from analysis if:
1. JSON parse failure rate > 10% of rounds (prompt format failure)
2. Single-session API cost > $0.10 (cost anomaly indicating runaway token usage)
3. Session terminated before round 25 (game completion failure)
4. JSONL log is incomplete (missing round events between round 1 and the final round)

Excluded sessions are logged to `data/study1/exclusions.jsonl` with reason codes. The number of excluded sessions per cell is reported in the paper alongside main results.

---

## 9. Open Science Commitments

- **Pre-registration:** This document is registered on OSF before Phase 1 data collection begins.
- **Open code:** Analysis stubs (H1–H5) committed at pre-registration timestamp. Full analysis code released alongside paper submission.
- **Open data:** Full JSONL game logs (4,000+ sessions) released on OSF/Zenodo with paper submission.
- **CFIM as benchmark:** Released as a standalone artifact for community use, with documentation for adding new model families.
- **Reproducibility:** `requirements-lock.txt` with exact pinned versions committed. Random seeds logged in all session metadata.

---

## 10. Timeline

| Milestone | Target date |
|---|---|
| OSF pre-registration submitted | 2026-03-15 |
| Phase 0 calibration complete | 2026-04-01 |
| Phase 1 (Study 1) data collection complete | 2026-05-15 |
| Study 2 (Harbour) complete | 2026-06-15 |
| Analysis and paper draft | 2026-07-15 |
| NeurIPS 2026 workshop submission | 2026-09-05 |
| AAMAS 2027 full paper submission | 2026-11-01 |

---

## 11. Author Information

[Author information will be added before OSF submission]

---

*End of pre-registration document. Word count: ~2800 words.*
