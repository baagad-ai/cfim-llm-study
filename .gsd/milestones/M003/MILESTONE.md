# M003: Phase 2 — Pairwise + Persona + Validation (185 Games)

**Status:** ⬜ Queued
**Depends on:** M002 complete + Phase 1 descriptive analysis done
**Target:** 185 games total (150 pairwise + 20 persona + 15 validation)
**Calendar estimate:** Weeks 6-8 (shifted by ~1 week from simulation repair sprint; 12-14 days)
**Budget:** ~$12.55

**Audit notes for Phase 2 design (from MASTER_AUDIT_2026-03-15):**
- **Phase 2C temporal validation:** Must specify which monoculture games to rerun and what drift metric to use BEFORE data collection. Draft spec: rerun 5 games per family (20 games total) with identical config as Phase 1; compare Gini and trade acceptance rate distributions via KS test. Drift threshold: p < 0.05 = drift detected.
- **H4 format confound:** Compact format is locked by D041–D044. Document explicitly in paper that format is held constant across families — otherwise H4 comparison (architecture vs persona) is confounded by framing. Add to limitations section.
- **DeepSeek R1 behavioral split:** Document in Phase 2B analysis that DeepSeek's memory (R1) and actions (V3) come from different model modes. This is a within-family confound for H4.

## Goal

Run the primary research contribution (pairwise games) plus the persona-vs-architecture experiment and temporal validation.

## Definition of Done

- [ ] All 6 pairwise pairs × 25 games complete (150 games)
- [ ] 20 persona-vs-architecture games complete (Phase 2B)
- [ ] 15 full-mix + temporal validation games complete (Phase 2C)
- [ ] Pairwise datasets built (per-pair JSONL logs)
- [ ] Exploitation index computed per game
- [ ] Cooperation tendency score computed per game
- [ ] Temporal validation: compare Phase 1 monoculture stats to Phase 2C monoculture stats (detect drift)
- [ ] Cost ≤ $12.55

## Slices

| Slice | Description | Games | Status |
|---|---|---|---|
| S01 | Pairwise Phase 2 (6 pairs × 25) | 150 | ⬜ planned |
| S02 | Phase 2B: Persona-vs-Architecture (20 games) | 20 | ⬜ planned |
| S03 | Phase 2C: Full-mix + Temporal Validation (15 games) | 15 | ⬜ planned |
| S04 | Phase 2 intermediate analysis (heatmap previews) | — | ⬜ planned |

## Pairwise Run Order (6 pairs)

1. Llama × Mistral (cheapest combination) — validate 3v3 setup
2. DeepSeek × Mistral
3. Llama × DeepSeek
4. Mistral × Gemini
5. Llama × Gemini
6. DeepSeek × Gemini (most expensive per game)

## Phase 2B Design (Persona-vs-Architecture)

- **Architecture condition (10 games):** Different model families, identical neutral prompts (no persona)
- **Persona condition (10 games):** Same model family, different persona prompts (e.g., "cooperative trader" vs "aggressive hoarder")
- Measure: variance on 5 metrics across conditions
- H4 test: is architecture variance > persona variance on ≥3 of 5 metrics?

## Data Organization

```
data/phase2/
  pairwise/
    llama_deepseek/  (25 games)
    llama_gemini/    (25 games)
    llama_mistral/   (25 games)
    deepseek_gemini/ (25 games)
    deepseek_mistral/(25 games)
    gemini_mistral/  (25 games)
  phase2b_persona/   (20 games)
  phase2c_validation/(15 games)
```
