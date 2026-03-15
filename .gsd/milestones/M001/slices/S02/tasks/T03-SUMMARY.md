---
id: T03
parent: S02
milestone: M001
provides:
  - parse_rne_response(raw) in src/prompts/rne_prompts.py — 4-strategy tolerant parser
  - tests/test_rne_prompts.py — 118 tests (up from 96), TestParseRNEResponse class added
  - scripts/run_rne.py — CLI entry point for Study 1 RNE sessions
  - _parse_action in rne_game.py delegates to parse_rne_response
  - _MECHANICS prompt fixed: agent-agnostic wording so Agent B (llama) proposes correct resources
key_files:
  - src/prompts/rne_prompts.py
  - tests/test_rne_prompts.py
  - scripts/run_rne.py
  - src/simulation/rne_game.py
key_decisions:
  - Array-wrapped dicts [{"action":"pass"}] — bracket extractor recovers inner dict (tolerant is better than strict here)
  - _MECHANICS string changed from "You are Agent A. You hold W and S." to agent-agnostic wording — original hardcoded Agent A identity caused llama (Agent B) to propose resources it doesn't hold, blocking all trades
patterns_established:
  - parse_rne_response is the canonical JSON extractor; _parse_action in rne_game.py delegates to it then validates action field
  - 4-strategy order: direct → fence-strip → bracket-counter → None; strategies are tried in order and first success wins
observability_surfaces:
  - parse_failure_count in summary.json counts rounds where all strategies failed
  - parse_failure events in game.jsonl carry agent id and raw[:200] for post-hoc debugging
  - scripts/run_rne.py prints M1, completed_trades, and cost per session to stdout
duration: ~90m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Tolerant parser + full test suite + smoke run

**Added `parse_rne_response` with 4-strategy fallback chain, wired into `RNERunner`, wrote `scripts/run_rne.py`, and confirmed real Mistral×Llama smoke run completes with ≥1 accepted trade at cost $0.0072.**

## What Happened

**Step 1–2: `parse_rne_response` implementation.**
Added to `src/prompts/rne_prompts.py` with the 4-strategy chain: (1) direct `json.loads`, (2) strip markdown fences via regex, (3) bracket-counter scan for first balanced `{...}` span, (4) return `None`. Handles `None` input, empty string, truncated JSON, prose-wrapped JSON, and array-wrapped dicts. Never raises.

**Step 3: Wire into `rne_game.py`.**
Imported `parse_rne_response`. Replaced `_parse_action`'s manual `json.loads` with a delegation call: `parse_rne_response(raw)` extracts the dict, then `_parse_action` validates the `action` field. The `strip_md` pre-pass from `llm_router` is still present but harmless (parse_rne_response handles fences redundantly).

**Step 4: Test suite.**
Added `TestParseRNEResponse` class (28 tests) to `tests/test_rne_prompts.py`. Covers all 4 strategies, edge cases (None, empty, whitespace, pure prose, JSON arrays, truncated JSON, arbitrary evil inputs), and return-type invariant. Total: 118 tests in the file.

**Step 5a: scripts/run_rne.py.** 
Script didn't exist — created it following the `scripts/run_game.py` pattern. Accepts `--family-a`, `--family-b`, `--condition`, `--disclosure`, `--framing`, `--games`, `--rounds`, `--data-dir`, `--mock` args.

**Step 5b: Smoke run debugging.**
First two smoke runs showed 0 completed trades despite 15 respond-accepts. Root cause: the `_MECHANICS` system prompt said "You are Agent A. You hold Wood (W) and Stone (S)" to **all** agents. Agent B (llama) received this and proposed giving W/S it doesn't hold, while wanting G/C back. All trades voided by `can_execute` inventory check.

Fix: rewrote `_MECHANICS` to agent-agnostic wording — "Two agents trade resources. One holds W and S; the other holds G and C. Your inventory is shown each round — only offer what you hold." This kept all token budgets under 300 (checked: max is 290 for C/social).

Third smoke run (2 games): session 1 completed 1 trade (M1=0.029, cost=$0.0072). Verification checks passed.

## Verification

```
pytest tests/test_rne.py tests/test_rne_prompts.py -v
→ 165 passed, 1 warning

# Must-have parser behaviors (all confirmed):
parse_rne_response('{"action":"propose","give":{"W":1},"want":{"G":1}}') → valid dict ✓
parse_rne_response('```json\n{"action":"pass"}\n```') → {"action":"pass"} ✓
parse_rne_response('Sure! {"action":"pass"} here you go') → {"action":"pass"} ✓
parse_rne_response('{"action":"prop') → None ✓
parse_rne_response('') → None ✓

# Smoke run (--games 2):
Session 1: id=3230fd13, M1=0.029, trades=1/35, cost=$0.0072
Session 2: id=e1c4ac76, M1=0.000, trades=0/35, cost=$0.0073

# Trade count across all sessions: 1 ≥ 1 ✓
# Summary assertion: cooperation_rate ∈ [0,1], cost ≤ $0.05 ✓
```

## Diagnostics

```bash
# Verify parser strategies directly
python3 -c "
from src.prompts.rne_prompts import parse_rne_response
print(parse_rne_response('{\"action\":\"pass\"}'))          # Strategy 1
print(parse_rne_response('\`\`\`json\n{\"action\":\"pass\"}\n\`\`\`'))  # Strategy 2
print(parse_rne_response('text {\"action\":\"pass\"} end'))  # Strategy 3
print(parse_rne_response('{\"action\":\"prop'))              # Strategy 4 → None
"

# Run a mock session (zero cost)
python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1 \
  --mock '{"action":"propose","give":{"W":1},"want":{"G":1}}'

# Count executed trades across all sessions
python3 -c "
import json, pathlib
count = sum(
    1 for p in pathlib.Path('data/study1').glob('*/game.jsonl')
    for line in p.read_text().splitlines()
    if line.strip() and json.loads(line).get('event')=='trade_result' and json.loads(line).get('accepted')
)
print('Executed trades:', count)
"
```

Note: `grep '"event".*"trade_executed"'` in the slice plan verification does NOT match real event names. Actual event is `trade_result` with `accepted: true`. Use the python3 counting command above instead.

## Deviations

- **`scripts/run_rne.py` was not mentioned in S02-PLAN "Files Likely Touched"** but is required by the verification command — created from scratch.
- **`_MECHANICS` string updated** (was "You are Agent A. You hold W and S"). Fixed agent-identity confusion bug that caused 100% trade failure in smoke runs. No T01/T02 test failures from this change — token budgets still met (max 290 tok vs 300 budget).
- **Test for array-wrapped JSON updated**: initial assumption was `[{"action":"pass"}]` → None. Actual behavior: bracket extractor recovers inner dict (correct for a tolerant parser). Test updated to document correct behavior.

## Known Issues

- `grep '"event".*"trade_executed"'` in slice plan verification never matches (event is `trade_result` with `accepted:true`, not a separate `trade_executed` event). Slice plan verification command is wrong — documented in Diagnostics above.
- Stochastic trade rate: 1 of 2 smoke sessions achieved ≥1 trade. With 35 rounds and random LLM proposals, some sessions will produce 0 trades (models fail to coordinate). This is expected behavior, not a bug. Study design calls for multiple sessions per condition precisely because of this variance.

## Files Created/Modified

- `src/prompts/rne_prompts.py` — added `parse_rne_response`, `import json`, `import re`; updated `_MECHANICS` to agent-agnostic wording; updated module docstring
- `tests/test_rne_prompts.py` — added `TestParseRNEResponse` (28 tests); updated import to include `parse_rne_response`; total 118 tests
- `src/simulation/rne_game.py` — imported `parse_rne_response`; `_parse_action` now delegates to it
- `scripts/run_rne.py` — new file; CLI entry point for Study 1 RNE sessions
