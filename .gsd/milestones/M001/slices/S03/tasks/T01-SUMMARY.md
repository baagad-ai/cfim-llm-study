---
id: T01
parent: S03
milestone: M001
provides:
  - src/prompts/json_utils.py — tolerant parser + format_inventory + get_completion_kwargs
  - src/prompts/__init__.py — public exports wired
key_files:
  - src/prompts/json_utils.py
  - src/prompts/__init__.py
key_decisions:
  - Bracket-counter scan in extract_first_json_object (pre-specified in S03-RESEARCH; documented here for completeness)
  - strip_md imported from llm_router — not copied
  - parse_agent_response returns None (not fallback dict) on unrecoverable failure
patterns_established:
  - 4-strategy fallback chain: strip_md → strip_think → bracket-counter extract → None
  - WARNING log per fallback strategy with 80-char input preview for diagnosability
  - Only json.JSONDecodeError/ValueError/TypeError caught; all other exceptions propagate
observability_surfaces:
  - logging.WARNING per fallback strategy; grep on "parse_agent_response" reveals parse degradation rate
  - Returns None so caller fallback paths are explicitly exercised and testable
duration: ~20m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Implement json_utils.py with tolerant parser and formatting helpers

**Implemented `src/prompts/json_utils.py` with 4-strategy tolerant JSON parser, compact inventory formatter, and per-provider kwarg lookup; all 6 spot-check assertions pass.**

## What Happened

Created `src/prompts/json_utils.py` with:

- `parse_agent_response(raw, schema) -> dict | None` — 4-strategy fallback chain: (1) `strip_md` + direct `json.loads`, (2) `strip_think` + `json.loads`, (3) bracket-counter `extract_first_json_object` + `json.loads`, (4) return `None`. Logs at WARNING for each fallback strategy used (not strategy 1). The bracket counter tracks open/close braces with string-escape awareness — correctly handles nested dicts and avoids the greedy `re.search` pitfall.
- `strip_think(text) -> str` — regex strips leading `<think>...</think>` block with `re.DOTALL`.
- `extract_first_json_object(text) -> str | None` — bracket-counter scan; no regex brace matching.
- `format_inventory(inv) -> str` — fixed W S G C F ordering, compact `W2 S3 G4 C1 F0` output.
- `get_completion_kwargs(model_family) -> dict` — shallow copy of `PROVIDER_KWARGS[model_family]`; raises KeyError on unknown family.

Updated `src/prompts/__init__.py` to export the three public functions.

## Verification

Full task-plan spot-check (6 assertions):
```
python -c "... (T01 spot-check) ..." → T01 ok
```

Base verification command:
```
python -c "from src.prompts.json_utils import ...; assert parse_agent_response('...', {}) == {'a':1}; assert parse_agent_response('{\"a\": \"b', {}) is None; print('ok')" → ok
```

Additional checks:
- Strategy 3 (embedded JSON): `'Here is my action: {"action_type":"build"} done.'` → `{'action_type': 'build'}` ✓
- `get_completion_kwargs('gemini')` has no `response_format` ✓
- `get_completion_kwargs('mistral')` has `response_format` ✓
- `get_completion_kwargs('unknown')` raises `KeyError` ✓
- `from src.prompts import parse_agent_response, format_inventory, get_completion_kwargs` works ✓

Slice-level gate:
```
pytest tests/test_smoke.py -v → 5 passed ✓ (no regressions from __init__.py changes)
```

Source inspection:
- `re.search` appears only in docstring comment — no functional regex brace matching
- No `def strip_md` in json_utils.py — imported from llm_router
- Exception scope: only `json.JSONDecodeError, ValueError, TypeError` caught (no bare `except Exception`)

## Diagnostics

```bash
# Quick single-case smoke
python -c "from src.prompts.json_utils import parse_agent_response; print(parse_agent_response('<think>r</think>\n{\"action_type\":\"hoard\"}', {}))"

# Parse degradation check at runtime
grep "parse_agent_response.*strategy" <logfile>
```

WARNING logs include 80-char raw input preview — sufficient to identify which model/prompt is producing malformed output.

## Deviations

none — implementation followed the task plan exactly.

## Known Issues

none

## Files Created/Modified

- `src/prompts/json_utils.py` — created; tolerant parser, format_inventory, get_completion_kwargs
- `src/prompts/__init__.py` — updated; added public exports for the three functions
