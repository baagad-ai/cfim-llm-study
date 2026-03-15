# M003: Phase 2 — Pairwise + Persona + Validation (185 Games)

**Status:** ⬜ Queued
**Depends on:** M002 complete + Phase 1 descriptive analysis done
**Target:** 185 games total (150 pairwise + 20 persona + 15 validation)
**Calendar estimate:** Weeks 5-7 (12-14 days)
**Budget:** ~$12.55

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
