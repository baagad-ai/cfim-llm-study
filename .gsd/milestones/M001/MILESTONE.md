# M001: Infrastructure + Phase 0

**Status:** 🔄 Active
**Started:** 2026-03-15
**Target completion:** ~2026-03-29 (2 weeks)
**Games in this milestone:** 30 (calibration + format ablation + GM sensitivity)

## Goal

Build the complete simulation infrastructure and validate it with 30 calibration games before any production data is collected.

## Definition of Done

- [x] Python venv with base dependencies installed (litellm, python-dotenv)
- [x] LiteLLM routing for all 4 providers with API key verification
- [ ] Full dependency install (concordia, polars, analysis stack)
- [ ] Concordia v2.0 integrated (marketplace evaluation done, Trade Island components implemented)
- [ ] All 6 prompt templates implemented (cache-optimized, prefix-first)
- [ ] JSON mode / parse strategy confirmed per provider (workarounds documented ✅ in DECISIONS.md)
- [ ] Phase 0 format ablation complete: >90% JSON parse rate confirmed per model
- [ ] Phase 0 GM sensitivity: Mistral GM vs Llama GM confound quantified
- [ ] 30 calibration games complete, logs in JSONL format
- [ ] OSF account created, H1-H4 hypotheses registered, analysis stubs committed
- [ ] Cost burned ≤ $1.50
- [ ] Git committed with version-pinned requirements.txt (pinned after full install)

## Slices

| Slice | Description | Status |
|---|---|---|
| S01 | LiteLLM + Environment Setup | ✅ COMPLETE |
| S02 | Concordia v2.0 Integration + Trade Island | ⬜ next |
| S03 | Prompt Templates + JSON Mode Validation | ⬜ planned |
| S04 | Phase 0: Format Ablation + GM Sensitivity (30 games) | ⬜ planned |
| S05 | OSF Pre-Registration + Analysis Stubs | ⬜ planned |

## Risks (Updated)

1. **Concordia v2.0 marketplace may not fit Trade Island mechanics** → Custom components needed (adds ~1 week). Evaluate first before building anything.
2. ~~**Gemini thinking mode token inflation**~~ → RESOLVED (D020-D022): `thinking={'type':'disabled','budget_tokens':0}` zeroes reasoning_tokens. Verified in S01.
3. ~~**DeepSeek direct API blocked from India**~~ → RESOLVED (D019): OpenRouter proxy works, json_object mode confirmed.
4. **Mistral version changed** → RESOLVED (D018): using `mistral-small-2506` in place of `3.1-2503`.
5. **Phase 0 JSON parse rate <90% on any model** → Switch to verbose format for that model only.
6. **Gemini RPM limits** → Paid tier active. Burst of 8 calls showed 2 transient 429s. LiteLLM retry (3×, 2s) will handle. Monitor during Phase 0.

## Exit Criteria

M001 exits to M002 **only when**:
- All 30 calibration games have valid JSONL logs
- OSF pre-registration is confirmed (registration ID in metrics.json)
- Phase 0 format decision documented in DECISIONS.md
- GM confound quantified and documented
- Full dependency stack installed and `requirements-lock.txt` committed
