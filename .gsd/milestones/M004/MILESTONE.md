# M004: Analysis + Writing

**Status:** ⬜ Queued
**Depends on:** M003 complete
**Calendar estimate:** Weeks 8-13 (5-6 weeks)
**Budget:** ~$0 (local compute only)

## Goal

Complete statistical analysis, generate all paper figures, write NeurIPS 2026 workshop short paper, prepare open-source deliverables.

## Definition of Done

- [ ] All 4 pre-registered hypotheses tested (H1-H4)
- [ ] 4×4 pairwise heatmaps generated (VP ratio, trade acceptance, exploitation index)
- [ ] Three-track behavioral classifier trained and evaluated
- [ ] Behavioral drift plots (5-round rolling windows, 8 plots total)
- [ ] NeurIPS 2026 workshop short paper submitted
- [ ] AAMAS 2027 full paper submitted
- [ ] arXiv preprint live
- [ ] concordia-pairwise library released (GitHub + pip)
- [ ] model-pairwise-benchmark tool released
- [ ] trade-island-dataset uploaded to Hugging Face

## Slices

| Slice | Description | Status |
|---|---|---|
| S01 | Full statistical analysis (H1-H4 + descriptives + classifier) | ⬜ planned |
| S02 | Figures + visualizations (heatmaps, drift plots, bar charts) | ⬜ planned |
| S03 | Paper writing (NeurIPS short + AAMAS full) | ⬜ planned |
| S04 | Open-source release prep (concordia-pairwise + benchmark + dataset) | ⬜ planned |

## Key Figures (Paper Signature)

1. **4×4 pairwise heatmap matrix** — VP ratio per matchup (main contribution figure)
2. **Trade acceptance heatmap** — cross-family acceptance rates
3. **Exploitation index heatmap** — which families exploit which
4. **Behavioral drift plots** — per-family 5-round rolling windows (4 models × monoculture + pairwise)
5. **Architecture vs Persona variance comparison** — bar chart for H4

## Open-Source Deliverables

- `concordia-pairwise`: pip-installable library. LiteLLM + Concordia v2.0 + Trade Island. All dependencies version-pinned. MIT license.
- `model-pairwise-benchmark`: `python benchmark.py --model-a llama-70b --model-b deepseek-chat --games 25`
- `trade-island-dataset`: 335+ game JSONL logs on Hugging Face Datasets. Full schema documentation.
- `analysis-notebooks/`: Reproducible Jupyter notebooks for all figures and tests.

## Paper Positioning (from MASTER_AUDIT_2026-03-15)

**Key differentiation from FAIRGAME/related work:**
- FAIRGAME (Buscemi et al., 2025) and "More at Stake" (Buscemi et al., 2026): 2-player matrix games. Our contribution: 6-player, multi-issue, multi-round resource trading game with VP victory. Richer strategic space.
- H4 (architecture vs persona variance) is the most publishable finding regardless of direction: architecture > prompt → contradicts framing-dominance literature; architecture < prompt → confirms framing dominance in economic settings. Either way publishable.
- Null result contingency: if all families produce statistically identical behavior, publish as "evidence against model-family behavioral attribution" — this is a valid contribution.
- Add explicit limitations: (a) compact English-only prompts may suppress cross-linguistic behavioral variance, (b) DeepSeek R1/V3 behavioral split, (c) temporal model instability (mitigated by Phase 2C but residual), (d) single economic game type.

**Related work to add in writing (S03):**
- FAIRGAME framework (Buscemi et al., 2025)
- "More at Stake" (Buscemi et al., 2026)
- "Understanding LLM Agent Behaviours via Game Theory" (Huynh et al., 2025)

## Writing Timeline

| Week | Activity |
|---|---|
| 8 | Full statistical analysis (implement stubs from M001/S05) |
| 9 | Figure generation + classifier training |
| 10 | Paper writing (NeurIPS workshop version, 4-6 pages) |
| 11 | Revision + peer feedback |
| 12 | Submit NeurIPS workshop. Begin AAMAS full paper expansion. |
| 13 | arXiv preprint. Open-source release. Blog post. |
