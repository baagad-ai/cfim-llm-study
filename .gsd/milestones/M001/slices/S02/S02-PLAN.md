# S02: RNE Prompt Architecture

**Goal:** Build `src/prompts/rne_prompts.py` with correct system prompts for all 3 game conditions × 3 framings × 2 disclosure variants. Wire into `RNERunner`. Add tolerant `parse_rne_response`. Confirm real Mistral×Llama smoke run completes with ≥1 accepted trade.
**Demo:** `python scripts/run_rne.py --family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1` completes 35 rounds. `grep '"event":"trade_executed"' data/study1/*/game.jsonl | wc -l` → ≥1. `total_cost_usd ≤ 0.05` in summary.json.

## Must-Haves

- `src/prompts/rne_prompts.py`:
  - `build_system_prompt(condition, framing)` — static prefix per (condition × framing) pair; 9 cached variants (3 conditions × 3 framings)
  - `build_round_messages(config, round_num, agent_id, inventory, history, opponent_family=None)` — includes disclosure injection when `config.disclosure == "disclosed"`
  - `parse_rne_response(raw)` — tolerant parser; handles valid JSON, fenced JSON, JSON with surrounding text, truncated JSON; returns `dict | None`
- `tests/test_rne_prompts.py` — parse rate tests across all 4 failure modes; disclosure injection verified; framing variant token counts within budget
- `RNERunner` wired to call `build_round_messages` and `parse_rne_response`

## Proof Level

- Contract (prompt module interface + parser correctness)
- Mock-mode only — no real API calls needed in tests

## Verification

```bash
source .venv/bin/activate && pytest tests/test_rne.py tests/test_rne_prompts.py -v
# → all tests pass (including new prompt tests)

python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1

grep '"event".*"trade_executed"' data/study1/*/game.jsonl | wc -l
# → ≥1

python3 -c "
import json, pathlib
s = json.loads(next(pathlib.Path('data/study1').glob('*/summary.json')).read_text())
assert 0.0 <= s['cooperation_rate'] <= 1.0
assert s['total_cost_usd'] <= 0.05
print('smoke ok, cost:', s['total_cost_usd'])
"
```

## Tasks

- [x] **T01: System prompt variants — 3 conditions × 3 framings** `est:1h`
  > Write `build_system_prompt(condition, framing)` with 9 cached variants. Condition A=coordination, B=mixed-motive, C=asymmetric power. Framing neutral/social/strategic. Wire into RNERunner.

- [x] **T02: Round messages + disclosure injection** `est:1h`
  > Write `build_round_messages(config, round_num, agent_id, inventory, history, opponent_family=None)`. Inject opponent family name when `config.disclosure == "disclosed"`. Cover both disclosure variants in `test_rne_prompts.py`.

- [x] **T03: Tolerant parser + full test suite + smoke run** `est:45m`
  > Write `parse_rne_response(raw)` handling valid JSON, fenced JSON, surrounded text, truncated JSON. Wire parser into RNERunner. Run real Mistral×Llama smoke game. Verify ≥1 accepted trade and cost ≤$0.05.

## Files Likely Touched

- `src/prompts/rne_prompts.py` — new
- `src/simulation/rne_game.py` — wire in prompt/parser calls
- `tests/test_rne_prompts.py` — new
