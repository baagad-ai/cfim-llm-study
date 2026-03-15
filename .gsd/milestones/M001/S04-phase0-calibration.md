# S04: Phase 0 — Format Ablation + GM Sensitivity (30 games)

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 3-4 days
**Requirements:** R004
**Budget:** ~$1.50

## Goal

Validate that compact prompt format works reliably for each model (>90% JSON parse rate), quantify GM confound, and run 10+ calibration games to confirm simulation mechanics.

## Tasks

### T01: Format ablation test (80 calls, ~$0.50)
- For each model (4 models × 20 calls each = 80 calls):
  - Send identical game state in COMPACT format (blueprint §2.2 templates)
  - Send identical game state in VERBOSE format (full English, no abbreviations)
  - Record: JSON parse success, action quality (valid action type, valid target/resource), latency
- Decision rule: if COMPACT produces <90% valid JSON on any model → use VERBOSE for that model only
- Document format decision in DECISIONS.md

### T02: GM sensitivity test (10 games)
- Run 5 games with Mistral Small as GM
- Run 5 games with Llama 70B as GM
- Same agent configuration (all Mistral agents for comparability, cheapest setup)
- Measure: VP distribution, trade acceptance rate, game outcome
- If GM type produces statistically different outcomes → add GM identity as covariate in all analysis models
- Document finding in DECISIONS.md

### T03: Calibration games (20 monoculture games, mixed models)
- Run 5 games per model family (Llama, DeepSeek, Gemini, Mistral)
- Purpose: validate mechanics, check for degenerate behavior (e.g., all agents hoarding, no trades, all games ending early)
- Check: do agents trade? Do VPs accumulate across rounds? Does grain scarcity matter?
- If any model produces <5% trade acceptance or >80% wait actions → diagnose prompt issue before Phase 1

### T04: Cost tracking validation
- After 30 calibration games: total cost should be ≤ $1.50
- Verify LiteLLM cost attribution is correct (per-model, per-game breakdown)
- Verify budget cap ($80) is tracked correctly
- Update metrics.json with actual phase0 cost

### T05: Phase 0 analysis report
- Create `data/phase0/PHASE0_REPORT.md`
- Include: JSON parse rates per model, format decisions, GM confound finding, calibration game summary statistics
- Go/no-go recommendation for Phase 1

## Acceptance Criteria

- [ ] 80 format-ablation calls complete, parse rates documented per model
- [ ] Format decision recorded in DECISIONS.md (compact or verbose per model)
- [ ] 10 GM sensitivity games complete, confound quantified
- [ ] 20 calibration games complete with valid JSONL logs
- [ ] No degenerate behavior observed (or diagnosed and fixed)
- [ ] Total Phase 0 cost ≤ $1.50
- [ ] `data/phase0/PHASE0_REPORT.md` written with go/no-go recommendation

## Decision Gate

**Phase 1 does NOT start until:**
1. Phase 0 report is written
2. Format decisions are locked (DECISIONS.md updated)
3. OSF pre-registration is complete (S05)
4. Any calibration-discovered issues are fixed and re-tested

## Notes

- Run calibration games sequentially (not parallel) — easier to debug issues
- Keep detailed notes on any unexpected agent behavior during calibration
- If Gemini thinking tokens appear in logs (output token count anomalously high) → fix thinking_budget enforcement before proceeding
- DeepSeek parse failures: inspect raw responses for reasoning chains leaking into output
