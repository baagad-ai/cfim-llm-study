# M003: Study 2 Harbour + Final Analysis

**Status:** ⬜ Queued
**Depends on:** M002 complete (full CFIM dataset assembled)
**Budget:** ~$15 (Study 2 Harbour games)
**Calendar estimate:** ~1.5 weeks after M002

## Goal

Run Study 2 (Harbour 6-agent games) to test ecological validity of CFIM patterns. Build the complete CFIM matrix. Run all pre-registered hypothesis tests (H1–H5).

## Success Criteria

- Study 2: ≥80 Harbour games complete (4 mono × 20 + mixed compositions from Study 1 findings)
- H1–H5 all tested and results recorded (null results are acceptable)
- 7×7 CFIM heatmap matrix generated (M1 cooperation rate, M2 exploitation delta)
- `data/cfim_matrix.json` — full CFIM matrix with M1–M4 per cell (mean ± CI)

## Definition of Done

- [ ] ≥80 Harbour games complete (Study 2)
- [ ] H1 (Wilcoxon diagonal vs off-diagonal) — result recorded
- [ ] H2 (LRT mixed-effects logistic) — result recorded
- [ ] H3 (|M6| identity sensitivity) — result recorded
- [ ] H4 (Kruskal-Wallis adaptation lag across pairs) — result recorded
- [ ] H5 (OLS bilateral M1 → Study 2 VP variance) — result recorded
- [ ] CFIM matrix exported as `data/cfim_matrix.json` + PNG heatmaps
- [ ] Study 2 data in `data/study2/`

## Slices

| Slice | Description | Status |
|---|---|---|
| S01 | Harbour engine (Study 2) | ⬜ planned |
| S02 | Study 2 mono + mixed games (≥80) | ⬜ planned |
| S03 | H1–H5 statistical analysis | ⬜ planned |
| S04 | CFIM matrix construction + heatmaps | ⬜ planned |

## Key Design Constraints (from SIMULATION_DESIGN.md §3.6)

- Mono condition: all 6 agents same family (4 families × 20 games = 80 games)
- Mixed condition: compositions designed from Study 1 M1 findings (pair the highest-M1 with lowest-M1 families in 3v3 split)
- H5 test: Study 2 VP variance ~ mean bilateral M1 from Study 1 for the specific pairs present (linear regression, R²>0.15, p<0.05)

## Data Organization

```
data/
  study2/
    {game_id}/
      game.jsonl
      summary.json
  cfim_matrix.json      ← M1–M4 per cell across 28 pairs × 3 conditions
  figures/
    cfim_heatmap_m1.png
    cfim_heatmap_m2.png
    adaptation_lag_matrix.png
```
