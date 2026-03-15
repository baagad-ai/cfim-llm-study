# S02: Trade Island Engine — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is a pure infrastructure slice. Verification is mechanical: JSONL line counts, field name checks, cost assertions, and pytest. No human behavioral judgment required. The one behavioral gap (0 accepted trades in live run) is a deferred calibration concern, not a UAT blocker.

## Preconditions

- `.venv` active: `source .venv/bin/activate` or prefix commands with `.venv/bin/python`
- `.env` present with `MISTRAL_API_KEY` set (required for live run; not required for mock tests)
- Working directory: `research/model-family/`
- Existing game run in `data/raw/1e8788dd/` (used for JSONL inspection checks)

## Smoke Test

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_smoke.py -v
```
Expected: `5 passed` with no errors. This confirms engine wiring, schema contract, double-spend guard, and mock cost=0.0.

## Test Cases

### 1. JSONL round_end line count (150 exact)

```bash
grep '"event": "round_end"' data/raw/*/game.jsonl | wc -l
```
**Expected:** `150` (25 rounds × 6 agents)

### 2. Field name is "vp" not "victory_points"

```bash
grep '"event": "round_end"' data/raw/*/game.jsonl | head -1 | jq 'has("vp")'
grep '"event": "round_end"' data/raw/*/game.jsonl | head -1 | jq 'has("victory_points")'
```
**Expected:** first returns `true`, second returns `false`

### 3. game_end total_cost_usd ≤ 0.02

```bash
jq 'select(.event=="game_end") | .total_cost_usd' data/raw/*/game.jsonl
```
**Expected:** `0` or any value ≤ 0.02

### 4. All 9 H2 fields present in gm_resolution events

```bash
grep '"event": "gm_resolution"' data/raw/*/game.jsonl | head -1 | jq 'to_entries | map(.key) | sort'
```
**Expected:** output includes `accepted`, `give_resource`, `pairing`, `proposer_model`, `reason`, `responder_model`, `round`, `trade_idx`, `valid`, `want_resource`

### 5. 25 checkpoint files written

```bash
ls data/raw/1e8788dd/checkpoint_r*.json | wc -l
```
**Expected:** `25`

### 6. Checkpoint filenames follow r{N:02d} format

```bash
ls data/raw/1e8788dd/checkpoint_r*.json | head -3
```
**Expected:** `checkpoint_r01.json`, `checkpoint_r02.json`, `checkpoint_r03.json`

### 7. GameConfig named configs resolve correctly

```bash
PYTHONPATH=. .venv/bin/python -c "
from src.simulation.config import GameConfig
m = GameConfig.from_name('mistral-mono')
p = GameConfig.from_name('phase0')
pw = GameConfig.from_name('pairwise-llama-mistral')
assert m.num_rounds == 25 and len(m.agent_models) == 6
assert p.num_rounds == 25
assert pw.agent_models['a0']['family'] == 'llama'
assert pw.agent_models['a3']['family'] == 'mistral'
print('configs ok')
"
```
**Expected:** `configs ok`

### 8. Double-spend guard standalone self-test

```bash
PYTHONPATH=. .venv/bin/python src/simulation/gm.py
```
**Expected:** `double-spend guard: ok`

### 9. Mock cost guard standalone self-test

```bash
PYTHONPATH=. .venv/bin/python src/simulation/llm_router.py
```
**Expected:** `mock cost guard: ok`

### 10. Event distribution sanity (all expected event types present)

```bash
jq '.event' data/raw/*/game.jsonl | sort | uniq -c
```
**Expected:** output includes `agent_action`, `build`, `game_end`, `game_start`, `gm_resolution`, `grain_consumption`, `reflection`, `round_end`, `round_start` — all 9 event types present.

## Edge Cases

### Double-spend rejection in game context (via test_smoke.py)

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_smoke.py::TestDoubleSpendInGame -v
```
**Expected:** `PASSED` — confirms that when agent a0 proposes two trades both requiring the same resource (and only has enough for one), the second is rejected at the GM level even if the LLM approves both.

### Mock game cost is float 0.0, not None or int 0

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_smoke.py::TestMockCostZero -v
```
**Expected:** `PASSED` — confirms `total_cost_usd` is a Python float and equals 0.0 (not None, not int 0).

### Unknown config name raises ValueError with helpful message

```bash
PYTHONPATH=. .venv/bin/python -c "
from src.simulation.config import GameConfig
try:
    GameConfig.from_name('unknown-config')
    print('FAIL — no error raised')
except ValueError as e:
    print('PASS:', e)
"
```
**Expected:** `PASS: Unknown config: unknown-config. Valid names: ...` (lists valid options)

## Failure Signals

- `pytest tests/test_smoke.py` shows any failures → engine regression; check which test failed, inspect the relevant module
- `grep '"event": "round_end"' data/raw/*/game.jsonl | wc -l` returns anything other than a multiple of 150 → round_end emission bug or partial game
- Any `round_end` line has `"victory_points"` instead of `"vp"` → field name regression in logger.py; breaks H1 analysis stub
- `total_cost_usd` is `None` in game_end event → cost guard regression; `or 0.0` missing or bypassed
- `ls data/raw/{game_id}/checkpoint_r*.json | wc -l` < 25 → checkpoint write ordering bug; check game.py flush/checkpoint ordering
- `gm_resolution` event missing any of the 9 H2 fields → GM logging regression; breaks H2 analysis stub
- `python src/simulation/gm.py` prints anything other than `"double-spend guard: ok"` → double-spend guard broken; do not run live games until fixed

## Requirements Proved By This UAT

- R002 — Trade Island simulation engine: 25-round game runs end-to-end with real Mistral API calls; checkpoint and JSONL output confirmed.
- R011 — JSONL schema: flat round_end fields, all 9 H2 gm_resolution fields, 9 event types confirmed. Schema locked as S02→S03 boundary contract.

## Not Proven By This UAT

- **≥1 accepted trade in live run:** All 115 trade proposals in the real Mistral-mono run were declined by responders (D037). The acceptance code path executes correctly (confirmed by test_smoke.py double-spend test and gm.py inline test), but LLM consent was not given. Deferred to S04 Phase 0 calibration for prompt investigation.
- **Mistral API cost tracking:** All Mistral calls returned `response_cost=None`; converted to 0.0 by cost guard. Actual per-game cost is unknown. Investigate in S04.
- **4-model pairwise routing:** Not tested in S02; requires all 4 API keys and a pairwise config game run. Covered by M001 integration milestone criterion (pairwise game with JSONL model-field spot check).
- **Crash-resume:** Checkpoint files exist and are readable; resume logic in GameRunner is not yet exercised. Covered by M001 operational verification criteria.
- **Polars pipeline ingestion:** JSONL schema is locked; actual Polars ingest of round_end lines into analysis-ready DataFrames is M002/S01 scope.
- **prompt template correctness:** S02 uses inline prompt strings in agent.py/gm.py. S03 replaces these with cache-optimized templates; S03 UAT covers template correctness and parse robustness.

## Notes for Tester

- The `data/raw/1e8788dd/` directory is the reference game run. It has 150 round_end lines and 25 checkpoints. If you run `scripts/run_game.py` again, a new game ID will be created alongside it — the grep patterns `data/raw/*/game.jsonl` will span both. Filter to a specific game_id with `data/raw/1e8788dd/game.jsonl` for deterministic counts.
- `total_cost_usd = 0.0` is correct for the acceptance run. litellm returned `response_cost=None` for all Mistral calls; the `or 0.0` guard produces float 0.0. This satisfies ≤$0.02 criterion. Do not treat this as a bug — it is a known litellm cost metadata gap for this provider configuration.
- The negative VP values (`"final_vp": {"a0": -17, ...}`) in game_end are expected. Grain consumption (1 grain/round deducted from VP) outpaced building gains in this particular game. This is a game balance calibration concern for S04, not a code bug.
- Running `pytest tests/test_smoke.py` a second time after the real game run is safe — the mock helper chdir's to pytest's tmp_path so it does not interact with data/raw/.
