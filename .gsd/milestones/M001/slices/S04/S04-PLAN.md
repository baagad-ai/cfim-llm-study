# S04: Phase 0 Calibration (30 games)

**Goal:** Repair simulation mechanics, validate fixes, complete 30 calibration games with scientifically valid data, lock prompt format per model, quantify GM confound, and produce a Go/No-Go report for Phase 1.

**Demo:** 5-game validation run shows VP in 3–9 range and trade acceptance >10%. Then `python scripts/run_game.py --config phase0 --games 30` completes; `grep '"accepted": true' data/raw/*/game.jsonl | wc -l` returns ≥30 (>10% of 300 proposals); `data/phase0/PHASE0_REPORT.md` contains a Go/No-Go decision; total cost ≤$1.50.

**Audit note (2026-03-15):** T01+T02 were completed as planned. T03 was blocked by MASTER_AUDIT_2026-03-15 which identified 8 critical simulation failures (CF1–CF8) making all data scientifically invalid (−17 to −20 VP starvation floor, 0% trade acceptance). Slice restructured from 4 tasks to 6: T01✅ T02✅ T03-FIX (repair sprint, new) T04 (5-game validation, new) T05 (30-game run, was T03) T06 (report, was T04).

---

## Must-Haves

- All CF issues (CF1–CF8) resolved and verified by unit tests before any game is run
- All SF issues (SF1–SF10) resolved
- 5-game validation run confirms: VP range 3–9, trade acceptance >10%, no starvation floor
- Mistral cost tracking returns `total_cost_usd > 0.0` in a real single-game run ✅ (T01 complete)
- GM provider derived dynamically ✅ (T01 complete)
- `resume_game(game_id)` and `--resume` CLI ✅ (T01 complete)
- Format decision (compact or verbose) locked per model in DECISIONS.md as D041–D044 ✅ (T02 complete)
- 30 Phase 0 calibration games complete in `data/raw/*/game.jsonl`
- Trade acceptance rate >10% across Phase 0 batch (retires D037 definitively)
- All 4 providers routed correctly
- ≥10 Llama-GM sensitivity games for confound quantification (upgraded from 5)
- `data/phase0/PHASE0_REPORT.md` with Go/No-Go recommendation
- Total cost ≤$1.50
- `requirements-lock.txt` committed (NH1)
- `.env.example` file created (NH2)

## Proof Level

- This slice proves: operational (real API calls; real data produced)
- Real runtime required: yes (T04: 5 live validation games; T05: 30 full games)
- Human/UAT required: yes — Phase 0 report Go/No-Go requires human review before Phase 1 begins

## Verification

```bash
# After T03-FIX: all tests pass
pytest tests/ -v
# → 23+ tests pass (including new CF/SF unit tests), 0 failures

# After T04: validation signal
for gid in $(ls -t data/raw | head -5); do
  jq 'select(.event=="game_end") | {total_cost_usd, winner_vp}' data/raw/$gid/game.jsonl
done
# VP: 3–9 range, no negatives

grep '"accepted": true' data/raw/*/game.jsonl | wc -l
# ≥5 accepted trades in 5 validation games (>10% of ~150 proposals)

# After T05: 30-game batch
jq -r 'select(.event=="game_end" and .config_name=="phase0") | .game_id' data/raw/*/game.jsonl | wc -l
# → 30

jq -r 'select(.event=="game_end" and .config_name=="phase0") | .total_cost_usd' \
  data/raw/*/game.jsonl | \
  python3 -c "import sys; vals=[float(l) for l in sys.stdin]; print(f'Total: \${sum(vals):.4f}, N={len(vals)}')"
# → Total ≤ $1.50

grep '"accepted": true' data/raw/*/game.jsonl | wc -l
# ≥30 (>10% of ~1500 proposals across 30 games)

# T06: report
test -f data/phase0/PHASE0_REPORT.md && grep -iE "GO|NO-GO" data/phase0/PHASE0_REPORT.md
```

## Observability / Diagnostics

- Runtime signals: `game_end.total_cost_usd`, `grep '"accepted": true'`, `grep "build_failed"`, `grep "gm_parse_failure"`
- New signals added in T03-FIX:
  - `build_failed` events with `reason` and `inventory` fields
  - `raw_action` field in `agent_action` events
  - `inventory` dict in `round_end` events
  - `model_version_used` field in `game_start` events (NH4)
- Failure visibility: `gm_parse_failure` events carry `raw_response` (500 char truncated)

## Integration Closure

- Upstream surfaces consumed: all of src/simulation/ and src/prompts/ (repaired in T03-FIX)
- New wiring introduced: resource specialization in `config.py`; grain income + Granary effect in `game.py`; key normalization in `game.py`; urgency injection in all prompt modules
- What remains before milestone is complete: S05 (OSF pre-registration)

---

## Tasks

- [x] **T01: Fix cost tracking, dynamic GM provider, and crash-resume** `est:45m`
  - COMPLETE. Mistral cost tracking fixed (litellm alias injection). GM provider dynamic. crash-resume implemented and tested. 6 smoke tests pass.

- [x] **T02: Format ablation (80 calls) and lock format decision per model** `est:1.5h wall`
  - COMPLETE. D041–D044 recorded in DECISIONS.md. All 4 models confirmed on compact format (≥90% parse rate).

- [x] **T03-FIX: Simulation repair sprint** `est:7h`
  - Why: MASTER_AUDIT_2026-03-15 identified 8 critical failures (CF1–CF8) making the simulation scientifically invalid, plus 10 should-fix issues (SF1–SF10) and 7 nice-to-have issues (NH1–NH7). Must fix CF1–CF8 + SF3+SF7+SF10 at minimum (minimum viable fix set). Strongly recommended: all SF issues and NH1+NH2+NH3+NH4+NH7.
  - See: T03-FIX-PLAN.md for full breakdown
  - Files: `src/simulation/game.py`, `src/simulation/config.py`, `src/prompts/agent_action.py`, `src/prompts/trade_response.py`, `src/prompts/reflection.py`, `src/simulation/llm_router.py`, `tests/test_smoke.py`, `tests/test_mechanics.py` (new), `requirements-lock.txt` (new), `.env.example` (new)
  - Done when: `pytest tests/ -v` passes with 0 failures; 5-game validation run shows VP 3–9, acceptance >10%.

- [x] **T04: 5-game validation run — confirm simulation is fixed** `est:30m wall`
  - Why: Before spending $1.50 on 30 games, validate that the repair sprint actually fixed the simulation. VP range and trade acceptance are the key signals.
  - Do: Run 5 phase0 games. Check VP distribution (should be 3–9, not −17 to −20). Check accepted trades (should be >10% of proposals). If VP is still negative or acceptance is still 0%, stop and return to T03-FIX.
  - Verify: `jq 'select(.event=="game_end") | .winner_vp' data/raw/*/game.jsonl` shows values in 3–9 range. `grep '"accepted": true' data/raw/*/game.jsonl | wc -l` ≥ 5.
  - Done when: VP range confirmed healthy; trade acceptance >0% confirmed; no starvation floor.

- [ ] **T05: Run 30 Phase 0 calibration games and verify signals** `est:3h wall`
  - (Previously T03 — gates now include: validated simulation, VP range 3–9 confirmed in T04)
  - Why: Primary data collection for Phase 0. All S04 must-haves around actual game data.
  - Do: Run `python scripts/run_game.py --config phase0 --games 30`. Monitor per-game cost. Verify ≥30 accepted trades (>10%). Verify 4-provider routing. Run ≥10 Llama-GM sensitivity games (upgraded from 5 per audit). Spot-check round_end event counts (should be 150 per game = 25 rounds × 6 agents). Check for no duplicate round_end events.
  - Verify: 30 games with `game_end`. ≥30 accepted trades. 4 families in model_assignments. Total cost ≤$1.50. No duplicate events.
  - Done when: 30 phase0 calibration games complete with valid data; ≥10 Llama-GM sensitivity games; acceptance >10%; cost ≤$1.50.

- [ ] **T06: Write Phase 0 report and update DECISIONS.md** `est:30m`
  - (Previously T04)
  - Why: Closes the slice. Synthesizes findings into a human-readable Go/No-Go document. Phase 1 (M002) is blocked until a human reviews this report and confirms Go.
  - Do: Extract metrics (cost, trade acceptance, VP distribution, GM confound). Write `data/phase0/PHASE0_REPORT.md` with 5 sections: (1) Format Decision, (2) Trade Acceptance Rate + D037 resolution, (3) GM Confound (≥10 Llama-GM games), (4) Cost Breakdown, (5) Go/No-Go Decision. Append D045–D048 to DECISIONS.md (see T06-PLAN.md for details).
  - Verify: `test -f data/phase0/PHASE0_REPORT.md`. All 5 sections present. Go/No-Go decision stated. DECISIONS.md updated.
  - Done when: `PHASE0_REPORT.md` exists with all 5 sections populated with real data; Go/No-Go decision stated; DECISIONS.md updated.

---

## Files Likely Touched

### T03-FIX
- `src/simulation/game.py` — grain income, Granary effect, resource specialization, key normalization, counter-offer fix, build_failed event, raw_action logging, inventory in round_end, early-win check, hoard fix
- `src/simulation/config.py` — resource specialization config, specialty archetypes, grain_income field
- `src/prompts/agent_action.py` — grain urgency, others' grain visible, full resource names
- `src/prompts/trade_response.py` — grain_rounds_left injection, building context, full resource schema
- `src/prompts/reflection.py` — game context enumeration, structured output format, memory compression
- `src/simulation/llm_router.py` — sleep(0.5) fix, model_version_used logging, Gemini thinking on reflections
- `tests/test_smoke.py` — token budget constant updated (SF7)
- `tests/test_mechanics.py` — new file: CF/SF unit tests (build affects inventory, grain consumption, hunger penalty, Granary income, resource specialization, pairing label, key normalization, build_failed event, raw_action logged, early-win condition)
- `requirements-lock.txt` — new: `pip freeze > requirements-lock.txt`
- `.env.example` — new: template with all required API key names

### T05
- `scripts/run_game.py` — `--gm-model` flag if not added in T01
- `scripts/run_gm_sensitivity.py` — ≥10 Llama-GM games
