# M001: Infrastructure + Phase 0

**Status:** 🔄 Active
**Started:** 2026-03-15
**Target completion:** ~2026-03-29 (2 weeks)
**Games in this milestone:** 30 (calibration + format ablation + GM sensitivity)

## Goal

Build the complete simulation infrastructure and validate it with 30 calibration games before any production data is collected.

## Definition of Done

- [ ] Python venv with all dependencies installed and pinned
- [ ] LiteLLM routing for all 4 providers with API key verification
- [ ] Concordia v2.0 integrated (marketplace evaluation done, Trade Island components implemented)
- [ ] All 6 prompt templates implemented (cache-optimized, prefix-first)
- [ ] JSON mode confirmed for each provider (with per-provider workarounds)
- [ ] Phase 0 format ablation complete: >90% JSON parse rate confirmed per model
- [ ] Phase 0 GM sensitivity: Mistral GM vs Llama GM confound quantified
- [ ] 30 calibration games complete, logs in JSONL format
- [ ] OSF account created, H1-H4 hypotheses registered, analysis stubs committed
- [ ] Cost burned ≤ $1.50
- [ ] Git committed with version-pinned requirements.txt

## Slices

| Slice | Description | Status |
|---|---|---|
| S01 | LiteLLM + Environment Setup | ⬜ planned |
| S02 | Concordia v2.0 Integration + Trade Island | ⬜ planned |
| S03 | Prompt Templates + JSON Mode Validation | ⬜ planned |
| S04 | Phase 0: Format Ablation + GM Sensitivity (30 games) | ⬜ planned |
| S05 | OSF Pre-Registration + Analysis Stubs | ⬜ planned |

## Risks

1. **Concordia v2.0 marketplace may not fit Trade Island mechanics** → Custom components needed (adds ~1 week)
2. **Gemini thinking mode token inflation** → thinking_budget=0 must be enforced at code layer, not just config
3. **DeepSeek JSON mode unreliability** → Fallback tolerant parser must be tested
4. **Phase 0 JSON parse rate <90% on any model** → Switch to verbose format for that model only

## Exit Criteria

M001 exits to M002 **only when**:
- All 30 calibration games have valid JSONL logs
- OSF pre-registration is confirmed (registration ID in metrics.json)
- Phase 0 format decision documented in DECISIONS.md
- GM confound quantified and documented
