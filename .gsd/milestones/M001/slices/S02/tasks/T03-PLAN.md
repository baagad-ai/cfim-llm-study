---
estimated_steps: 5
estimated_files: 3
---

# T03: Tolerant parser + full test suite + smoke run

**Slice:** S02 — RNE Prompt Architecture
**Milestone:** M001

## Description

Write `parse_rne_response(raw)` with a 4-strategy tolerant fallback chain. Write `tests/test_rne_prompts.py` covering all failure modes, disclosure injection, and token budgets. Then run the full slice verification smoke run.

## Steps

1. Add `parse_rne_response(raw: str) -> dict | None` to `src/prompts/rne_prompts.py`
2. Strategy chain: (1) direct `json.loads`, (2) strip markdown fences then parse, (3) bracket-counter extraction, (4) return `None`
3. Wire `parse_rne_response` into `RNERunner` — replace current response parsing
4. Write `tests/test_rne_prompts.py` with classes: `TestBuildSystemPrompt`, `TestBuildRoundMessages`, `TestParseRNEResponse`, `TestTokenBudgets`
5. Run full slice verification: `pytest tests/test_rne.py tests/test_rne_prompts.py -v` then smoke run

## Must-Haves

- [ ] `parse_rne_response('{"action":"propose","give":{"W":1},"want":{"G":1}}')` → valid dict
- [ ] `parse_rne_response('```json\n{"action":"pass"}\n```')` → `{"action":"pass"}`
- [ ] `parse_rne_response('Sure! {"action":"pass"} here you go')` → `{"action":"pass"}`
- [ ] `parse_rne_response('{"action":"prop')` → `None` (truncated)
- [ ] `parse_rne_response('')` → `None`
- [ ] `tests/test_rne_prompts.py` — ≥12 tests, all passing
- [ ] `pytest tests/test_rne.py tests/test_rne_prompts.py` — all pass

## Verification

```bash
source .venv/bin/activate
pytest tests/test_rne.py tests/test_rne_prompts.py -v
# → all pass

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

## Expected Output

- `src/prompts/rne_prompts.py` — updated with `parse_rne_response`
- `tests/test_rne_prompts.py` — new test file
- `src/simulation/rne_game.py` — updated to use `parse_rne_response`
