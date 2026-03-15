# M004: Paper + Open-Source Release

**Status:** ⬜ Queued
**Depends on:** M003 complete (H1–H5 results, CFIM matrix, heatmaps)
**Budget:** ~$0 (local compute only)
**Calendar estimate:** ~5 weeks after M003

## Goal

Write and submit the AAMAS 2027 paper and NeurIPS 2026 workshop short paper. Release the RNE environment and CFIM dataset as open-source.

## Success Criteria

- NeurIPS 2026 Foundation Models workshop submission (September 2026 deadline)
- AAMAS 2027 full paper submission (October 2026 deadline)
- arXiv preprint live
- RNE environment pip-installable (`pip install rne-game`)
- CFIM dataset on Hugging Face Datasets
- All analysis notebooks reproducible from raw JSONL

## Definition of Done

- [ ] AAMAS 2027 full paper submitted (8 pages + refs, GAAI track)
- [ ] NeurIPS 2026 workshop short paper submitted (4 pages)
- [ ] arXiv preprint live with DOI
- [ ] `rne-game` pip package released (MIT license)
- [ ] `cfim-dataset` on Hugging Face (3,360+ session JSONL logs + summary CSVs)
- [ ] Analysis notebooks reproducible: `jupyter nbconvert --execute` on all notebooks with no errors

## Slices

| Slice | Description | Status |
|---|---|---|
| S01 | Complete H1–H5 implementations + figures | ⬜ planned |
| S02 | Paper writing (NeurIPS short) | ⬜ planned |
| S03 | Paper expansion (AAMAS full) | ⬜ planned |
| S04 | Open-source release (rne-game + dataset) | ⬜ planned |

## Paper Positioning (SIMULATION_DESIGN.md §7)

| Related work | What they did | What we add |
|---|---|---|
| Akata et al. 2025 (NHB) | Cross-family PD games; aggregate heatmaps | Opponent-contingency analysis; identity disclosure; adaptation dynamics |
| "AI in the Mirror" (2025) | Self vs. non-self disclosure in PGG | Cross-family labels; 7 families; 3 game conditions |
| GAMA-Bench (2024) | Strategic reasoning performance | Behavioral adaptation and relational profiles |
| NetworkGames (2025) | 16×16 personality dyadic matrix | Model families as natural groupings; safety implications |

**Key differentiator:** We are the first paper to analyze whether a model's behavioral strategy changes as a function of *which opponent family* it faces. The CFIM is a reusable benchmark — every new model can be placed in the matrix.

## Open-Source Deliverables

- `rne-game`: pip-installable RNE environment. `RNERunner`, `RNEConfig`, prompts, parser. MIT license.
- `cfim-dataset`: All 3,360+ session JSONL logs + `summary.csv` on Hugging Face. Full schema documentation.
- `analysis-notebooks/`: Reproducible Jupyter notebooks for H1–H5, CFIM matrix, all figures.
- `cfim-benchmark`: One-command benchmarking: `cfim-run --family-a llama --family-b mistral --condition A --sessions 20`

## Writing Timeline

| Week | Activity |
|---|---|
| 1 | Implement H1–H5 stubs into full analysis; generate all figures |
| 2 | Write NeurIPS workshop short paper (4 pages) |
| 3 | Revision + peer feedback |
| 4 | Submit NeurIPS workshop. Begin AAMAS full paper expansion. |
| 5 | AAMAS full paper. arXiv preprint. Open-source release. Blog post. |
