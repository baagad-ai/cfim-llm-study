---
estimated_steps: 5
estimated_files: 3
---

# T02: Format ablation (80 calls) and lock format decision per model

**Slice:** S04 — Phase 0 Calibration (30 games)
**Milestone:** M001

## Description

The compact prompt format was validated for token budget in S03 but never tested for JSON parse reliability with real LLMs. Each model family may respond differently to compact vs verbose prompts. The 90% parse success threshold determines which format we use for all Phase 1 games — and that decision is irrevocable after OSF registration.

The ablation sends 20 compact + 20 verbose `call_llm()` calls per model (80 total), parses each response with `parse_agent_response()`, and records the parse strategy distribution. A model with compact parse rate ≥ 90% stays on compact; below 90% switches to verbose.

Estimated wall time: ~1 hour (80 calls × 0.5s sleep + API latency).

## Steps

1. **Add `build_act_messages_verbose()`** to `src/prompts/agent_action.py` as a new standalone function with the same signature as `build_act_messages()`. The verbose user message spells out resource names in full and uses complete identifiers:
   ```
   Round 5 of 25. You are agent a0 (mistral family).
   Inventory: wood=2, stone=3, grain=4, clay=1, fiber=0. VP: 6.
   Other agents: a1(vp=3), a2(vp=3), a3(vp=2), a4(vp=5), a5(vp=1).
   Choose your action.
   ```
   System message stays identical to `_build_system()` — the format test is on the user message shape only. Target ~215 tok total. Do NOT modify `build_act_messages()`.

2. **Write `scripts/run_format_ablation.py`**:
   - Import `call_llm` from `src.simulation.llm_router` and `parse_agent_response` from `src.prompts.json_utils`
   - Define a synthetic game-state fixture (realistic mid-game state)
   - For each of 4 models (4 entries from `GameConfig.from_name('phase0').agent_models`, one per family):
     - Send 20 calls with `build_act_messages()` (compact)
     - Send 20 calls with `build_act_messages_verbose()` (verbose)
     - For each call: parse with `parse_agent_response()`, classify as success (not None and has `action_type` key) or failure
   - Print per-model table: `compact: N/20 (P%), verbose: N/20 (P%), DECISION: compact|verbose`
   - Apply decision rule: compact rate ≥ 90% → compact; else verbose
   - If compact rate is between 85–90%, note it as "borderline, using verbose for safety"
   - Print final summary: `FORMAT DECISIONS: {llama: compact, deepseek: compact, gemini: verbose, mistral: compact}` (example)

3. **Run the ablation**: `python scripts/run_format_ablation.py 2>&1 | tee ablation_output.txt`
   - Monitor for any model showing <80% on both formats (would indicate a prompt bug, not a format issue)
   - If a model fails to parse even the verbose format >20% of the time, investigate before proceeding to T03

4. **Record format decisions in DECISIONS.md** — append D041–D044, one per model family. Each entry includes:
   - Compact parse rate (N/20)
   - Verbose parse rate (N/20)
   - Decision: compact or verbose
   - Rationale: threshold-based (≥90% compact wins; below → verbose)

5. **Verify token budget for verbose variant** — `python -c "from src.prompts.agent_action import build_act_messages_verbose; msgs = build_act_messages_verbose(...); total = sum(len(m['content']) for m in msgs) // 4; print(total)"` — should be 180–250 tok range.

## Must-Haves

- [ ] `build_act_messages_verbose()` exists in `agent_action.py` with same signature as compact variant; does NOT modify existing `build_act_messages()`
- [ ] `scripts/run_format_ablation.py` runs end-to-end without error on all 4 models
- [ ] Parse rates recorded for all 4 model families (compact AND verbose)
- [ ] D041–D044 appended to `.gsd/DECISIONS.md` with exact parse counts as evidence
- [ ] `pytest tests/test_prompts.py -v` still passes after `agent_action.py` change (18 tests)

## Verification

```bash
# Existing tests still pass after adding verbose function
pytest tests/test_prompts.py tests/test_smoke.py -v
# → 24 passed (18 + 6)

# Ablation runs (real API calls — ~1hr)
python scripts/run_format_ablation.py 2>&1 | tee ablation_output.txt
# → prints per-model parse rates and DECISION per model

# Decisions recorded
grep "D04[1-4]" .gsd/DECISIONS.md
# → 4 lines

# Token budget check for verbose
python -c "
from src.prompts.agent_action import build_act_messages_verbose
from src.simulation.config import GameConfig
c = GameConfig.from_name('phase0')
msgs = build_act_messages_verbose(
    'a0', 'mistral', 5,
    {'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0},
    6, [], {'a0':6,'a1':3,'a2':3,'a3':2,'a4':5,'a5':1},
    [], c.buildings
)
total = sum(len(m['content']) for m in msgs) // 4
print(f'verbose tokens: ~{total}')
assert 150 <= total <= 300, f'out of expected range: {total}'
print('ok')
"
```

## Inputs

- `src/prompts/agent_action.py` — extend with verbose variant
- `src/simulation/llm_router.py` — T01 complete (cost tracking working, cost alias injected)
- `src/prompts/json_utils.py` — `parse_agent_response()` for response classification
- `src/simulation/config.py` — `GameConfig.from_name('phase0')` to get 4-family model list

## Expected Output

- `src/prompts/agent_action.py` — `build_act_messages_verbose()` added; compact variant untouched
- `scripts/run_format_ablation.py` — new script; runs 80 real calls; prints per-model decision
- `.gsd/DECISIONS.md` — D041–D044 appended with compact/verbose parse rates and decision per family
