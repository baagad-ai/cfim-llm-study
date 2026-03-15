---
estimated_steps: 6
estimated_files: 5
---

# T01: Fix cost tracking, dynamic GM provider, and crash-resume

**Slice:** S04 — Phase 0 Calibration (30 games)
**Milestone:** M001

## Description

Three pre-existing gaps make real runs unobservable or incomplete: (1) `mistral/mistral-small-2506` is absent from litellm's model cost map, so all Mistral calls return `response_cost=None` and `total_cost_usd=0.0`; (2) `gm.py` hardcodes `provider="mistral"` in `_get_gm_verdicts()`, which will send Mistral-only kwargs to Groq for the Llama-GM sensitivity test; (3) `GameRunner` has no `resume_game()` method, so a mid-batch crash requires restarting all 30 games from scratch.

All three are surgical fixes of 10–25 lines each. They must all pass before T02/T03 run any real API calls.

## Steps

1. **Cost alias injection** — in `src/simulation/llm_router.py`, immediately after `import litellm` (before `litellm.drop_params = True`), add:
   ```python
   # Mistral pinned version is absent from litellm's built-in price map; alias it.
   # Values confirmed from litellm.model_cost['mistral/mistral-small-3-2-2506'].
   litellm.model_cost.setdefault(
       'mistral/mistral-small-2506',
       litellm.model_cost['mistral/mistral-small-3-2-2506']
   )
   ```
   Use `setdefault` so the injection is idempotent if litellm adds the model in a future version.

2. **Dynamic GM provider** — in `src/simulation/gm.py`, update `GM.__init__` to accept `provider: str | None = None` and derive it from `model_string` if not supplied:
   ```python
   self.provider: str = provider or model_string.split('/')[0]
   ```
   Replace the hardcoded `provider="mistral"` in `_get_gm_verdicts()` with `provider=self.provider`. In `src/simulation/game.py`, update the `GM(...)` construction call to pass `provider=config.gm_model.split('/')[0]` (or omit it — the default derivation handles it).

3. **`resume_game()` in `GameRunner`** — add method to `src/simulation/game.py`:
   - Find highest-numbered checkpoint: `sorted(Path(f"data/raw/{game_id}").glob("checkpoint_r*.json"))[-1]`
   - Load it with `json.load()`
   - Reconstruct `Agent` list: `Agent(**entry)` for each entry in `cp['agents']`
   - Wire cost tracking (same `_tracking_call_llm` pattern as `run_game()`)
   - Call `self._run(game_id=game_id, output_dir=..., cost_bucket=..., mock_response=..., start_round=cp['round'] + 1)` — `_run()` needs a new `start_round` parameter (default `1`) to skip already-completed rounds
   - The JSONL file is opened in `"a"` mode by `GameLogger` — appending from round N+1 is correct behavior

4. **`--resume GAME_ID` CLI arg** — add to `scripts/run_game.py`:
   ```python
   parser.add_argument('--resume', type=str, default=None, metavar='GAME_ID',
       help='Resume an interrupted game from its latest checkpoint.')
   ```
   When `args.resume` is set, call `runner.resume_game(args.resume)` instead of `runner.run_game()`.

5. **`test_crash_resume` in `tests/test_smoke.py`** — add a 6th test with a clean crash simulation:
   - Run a 3-round mock game using `_run_mock_game(num_rounds=3, tmp_path=tmp_path)` — this completes and writes `checkpoint_r01`, `checkpoint_r02`, `checkpoint_r03` plus 3×6=18 `round_end` events
   - Now simulate a "crash at round 3 of a 5-round game": create a `GameRunner` with `num_rounds=5`, call `resume_game(game_id)` with `mock_response=_MOCK_ACT_HOARD` — resume loads `checkpoint_r03` (highest) and calls `_run(start_round=4)`, running rounds 4–5
   - Assert total `round_end` events in the JSONL = (3 + 2) × 6 = 30 — the 3 completed rounds remain; 2 new rounds appended; no duplicates
   - Assert exactly 2 `game_end` events exist: one from the initial 3-round completion and one from the resume completion (this is acceptable — the resume run is a continuation, not a restart)
   - Assert `checkpoint_r04.json` and `checkpoint_r05.json` exist after resume

6. **Run real single Mistral game to verify cost > 0** — `python scripts/run_game.py --config mistral-mono --games 1`; check `jq 'select(.event=="game_end") | .total_cost_usd'` > 0.0. This is the T01 gate for all subsequent real-run work.

## Must-Haves

- [ ] `litellm.model_cost['mistral/mistral-small-2506']` populated at `llm_router.py` import time
- [ ] `GM.__init__` derives provider from `model_string` when not supplied; no hardcoded `"mistral"` in `_get_gm_verdicts()`
- [ ] `resume_game(game_id)` exists in `GameRunner`; loads highest-numbered checkpoint; reconstructs agents via `Agent(**entry)`
- [ ] `_run()` has `start_round` parameter so resume skips already-completed rounds
- [ ] `--resume GAME_ID` accepted by `run_game.py` CLI
- [ ] `test_crash_resume` passes — no duplicate `round_end` events after resume
- [ ] `pytest tests/test_smoke.py -v` → 6 passed (5 existing + 1 new)
- [ ] Real Mistral single-game `total_cost_usd > 0.0`

## Verification

```bash
# Unit gate
pytest tests/test_smoke.py -v
# → 6 passed

# Cost gate (real API call)
python scripts/run_game.py --config mistral-mono --games 1
LATEST=$(ls -t data/raw | head -1)
jq 'select(.event=="game_end") | .total_cost_usd' data/raw/$LATEST/game.jsonl
# → float > 0.0

# GM dynamic provider sanity (import only)
python -c "
from src.simulation.gm import GM
g = GM(model_string='groq/llama-3.3-70b-versatile')
print('GM provider:', g.provider)
assert g.provider == 'groq', g.provider
print('ok')
"

# Resume CLI arg
python scripts/run_game.py --help | grep resume
# → shows --resume argument
```

## Observability Impact

- Signals added/changed: `total_cost_usd` in `game_end` events now reflects real Mistral cost (previously always 0.0)
- How a future agent inspects this: `jq 'select(.event=="game_end") | .total_cost_usd' data/raw/*/game.jsonl` gives actual cost per game
- Failure state exposed: if cost is still 0.0 after fix, check `python -c "import litellm; print(litellm.model_cost.get('mistral/mistral-small-2506'))"` — should return cost dict, not None

## Inputs

- `src/simulation/llm_router.py` — add cost alias after `import litellm`
- `src/simulation/gm.py` — `GM.__init__` + `_get_gm_verdicts()` provider fix
- `src/simulation/game.py` — `resume_game()` method; `_run()` `start_round` param; GM constructor call
- `scripts/run_game.py` — `--resume` arg
- `tests/test_smoke.py` — `test_crash_resume`
- `data/raw/1e8788dd/checkpoint_r10.json` — confirmed checkpoint schema for resume reconstruction reference

## Expected Output

- `src/simulation/llm_router.py` — cost alias line added at top; Mistral games now report real cost
- `src/simulation/gm.py` — `GM(model_string, provider=None)` constructor; `self.provider` used in `_get_gm_verdicts()`
- `src/simulation/game.py` — `resume_game()` method; `_run(start_round=1)` default; GM constructor call updated
- `scripts/run_game.py` — `--resume GAME_ID` arg
- `tests/test_smoke.py` — 6th test `test_crash_resume` added; all 6 pass
