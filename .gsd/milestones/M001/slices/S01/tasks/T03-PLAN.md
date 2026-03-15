---
estimated_steps: 6
estimated_files: 3
---

# T03: CLI, Test Suite, and Smoke Run

**Slice:** S01 — RNE Engine + LLM Router
**Milestone:** M001

## Description

Wire the CLI, write the mock-mode test suite, then run a real 2-family smoke game (Mistral vs Llama) to retire the routing and schema risks.

## Steps

1. Write `scripts/run_rne.py` with argparse CLI
2. Write `tests/__init__.py` and `tests/test_rne.py` with 5 mock-mode tests
3. Run `pytest tests/test_rne.py -v` — all 5 must pass
4. Run real smoke game: `--family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1`
5. Verify JSONL output and summary.json
6. Confirm total cost ≤ $0.05

## Must-Haves

- [ ] `scripts/run_rne.py` accepts: `--family-a`, `--family-b`, `--condition` (A/B/C), `--disclosure` (blind/disclosed), `--framing` (neutral/social/strategic), `--games` (int), `--mock` (flag for mock responses); creates `data/study1/{session_id}/` before first write
- [ ] `tests/test_rne.py` — 5 tests:
  - `TestSchema`: round_end events have `session_id, family_a, family_b, round, agent, action_type, resources_after, cost_delta`
  - `TestDecay`: after 1 round with no trade, resource = `int(start * 0.9)`
  - `TestPerturbation`: perturbation event fires exactly at `config.perturbation_round` (use 5 in test)
  - `TestCooperationRate`: M1=1.0 when all rounds have compatible proposals in mock
  - `TestCostGuard`: `summary.json` total_cost_usd=0.0 for fully mocked session
- [ ] Real smoke game produces: `data/study1/*/game.jsonl` with ≥35 `round_end` events; `summary.json` with valid float M1; one `perturbation` event; `total_cost_usd ≤ 0.05`

## Verification

```bash
pytest tests/test_rne.py -v
# → 5 passed

python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1

grep '"event": "round_end"' data/study1/*/game.jsonl | wc -l
# → 70 (35 rounds × 2 agents)

grep '"event": "perturbation"' data/study1/*/game.jsonl | wc -l
# → 2 (1 per agent per game)

python -c "
import json, pathlib, glob
s = json.loads(list(pathlib.Path('data/study1').glob('*/summary.json'))[0].read_text())
assert 0.0 <= s['cooperation_rate'] <= 1.0
assert s['total_cost_usd'] <= 0.05
print('smoke ok, cost:', s['total_cost_usd'])
"
```

## Inputs

- `src/simulation/rne_game.py` — `RNERunner` (from T02)
- `src/simulation/config.py` — `RNEConfig`
- `.env` — API keys for real smoke run

## Expected Output

- `scripts/run_rne.py`
- `tests/__init__.py`
- `tests/test_rne.py`
- `data/study1/{session_id}/` — real smoke game output
