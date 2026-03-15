# S04: Phase 0 — Format Ablation + GM Sensitivity (30 games)

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 3-4 days
**Requirements:** R004
**Budget:** ~$1.50
**Depends on:** S02 (game engine), S03 (prompt templates)

## Goal

Validate compact prompt format works reliably for each model (>90% JSON parse rate), quantify GM confound, run calibration games to confirm simulation mechanics are sane before Phase 1.

## Context

30 games total, broken into 3 sub-phases:
- **Format ablation**: 80 isolated calls (not full games), ~$0.50
- **GM sensitivity**: 10 full games, ~$0.30
- **Calibration**: 20 full games (5 per model family), ~$0.70

Run order: format ablation → GM sensitivity → calibration games. Each gate must pass before proceeding.

## Tasks

### T01: Format ablation test (80 calls, ~$0.50)
Runner: `python scripts/run_phase0.py --task format-ablation`

For each model family (4 models × 20 calls each = 80 calls):
- Send identical realistic game state in **compact** format (blueprint §2.2 templates)
- Send identical game state in **verbose** format (full English sentences, no abbreviations)
- Record per call: JSON parse success (bool), action validity (valid act/target/resource), latency_ms

**Decision rule (pre-specified):**
- If compact format produces ≥90% valid JSON → use compact for that model
- If compact format produces <90% valid JSON → use verbose for that model only
- Document decision in DECISIONS.md as D024+

**Expected outcome based on S01 connectivity results:**
- Groq: compact should work (json_object enforced)
- DeepSeek: compact should work (json_object enforced via OpenRouter)
- Gemini: uncertain — fences may appear with complex prompts; fallback parser handles it
- Mistral: compact should work (json_object enforced)

### T02: GM sensitivity test (10 games, ~$0.30)
Runner: `python scripts/run_phase0.py --task gm-sensitivity`

Configuration:
- 5 games with **Mistral Small 2506** as GM (standard)
- 5 games with **Llama 3.3 70B** as GM (alternative)
- All 6 agents: Mistral (cheapest, simplest to control)
- Same random seeds for both sets (paired comparison)

Metrics to compare:
- Mean VP at round 25 (per-agent, per-game)
- Trade acceptance rate
- Mean game duration (rounds until first 12VP or round 25)

**Decision rule:**
- If Mann-Whitney U test shows significant difference (p<0.10) in any metric → add GM identity as covariate in all mixed-effects models
- Document finding in DECISIONS.md as D025

### T03: Calibration games (20 games, ~$0.70)
Runner: `python scripts/run_phase0.py --task calibration --model {llama|deepseek|gemini|mistral} --games 5`

5 games per model family (all monoculture — same family for all 6 agents).
Run order: Mistral → Llama → DeepSeek → Gemini (ascending cost).

**Quality gates — check after first game of each model:**
- JSON parse rate ≥ 90% across all action calls?
- Trade acceptance rate > 5% across game?
- ≥1 build action somewhere in the game?
- Cost within ±30% of expected (Mistral ~$0.015, Llama ~$0.058, DeepSeek ~$0.020, Gemini ~$0.099)?

If any gate fails → STOP that model, diagnose, fix before continuing.

**Degenerate behavior flags (requires investigation if triggered):**
- >80% of all actions are "wait" → prompt not engaging agents
- 0 trades accepted across entire game → agents not understanding trade mechanics
- 0 VP accumulated across game → building mechanic broken
- Any model consistently produces invalid JSON after fallback parser → prompt format issue

### T04: Phase 0 cost verification
After all 30 games (format ablation calls + 10 GM games + 20 calibration games):
- Total Phase 0 cost must be ≤ $1.50
- Update `metrics.json`: `cost_usd.burned`, `games_completed.phase0`
- Verify LiteLLM budget tracker is consistent with manual sum

### T05: Phase 0 analysis report
File: `data/phase0/PHASE0_REPORT.md`

Sections:
1. Format ablation results (table: model × format × parse_rate%)
2. Format decisions (compact vs verbose per model, reason)
3. GM sensitivity findings (test statistic, p-value, decision on covariate)
4. Calibration game summary stats (mean VP, trade acceptance, build rate per model)
5. Any degenerate behavior observed and resolution
6. Go / No-Go recommendation for Phase 1
7. Cost breakdown (actual vs budget)

## Acceptance Criteria

- [ ] 80 format-ablation calls complete, parse rates documented per model
- [ ] Format decision recorded in DECISIONS.md (D024+) for each model
- [ ] 10 GM sensitivity games complete with valid logs
- [ ] GM confound quantified and documented in DECISIONS.md
- [ ] 20 calibration games complete with valid JSONL logs (all 4 model families)
- [ ] No degenerate behavior in >20% of any model's games (or diagnosed and fixed)
- [ ] Total Phase 0 cost ≤ $1.50
- [ ] `data/phase0/PHASE0_REPORT.md` written with Go/No-Go decision

## Phase 1 Gate

**Phase 1 does NOT start until ALL of the following are confirmed:**
1. Phase 0 report is written and Go recommendation issued
2. All format decisions locked (DECISIONS.md)
3. OSF pre-registration complete (S05) — registration ID in metrics.json
4. Any calibration-discovered bugs are fixed and smoke-tested
