---
estimated_steps: 5
estimated_files: 2
---

# T01: Implement json_utils.py with tolerant parser and formatting helpers

**Slice:** S03 — Prompt Templates + Tolerant Parser
**Milestone:** M001

## Description

Create `src/prompts/json_utils.py` as the foundational utility module for S03. This module has three responsibilities: (1) `parse_agent_response()` — a multi-strategy tolerant JSON parser that returns `None` on unrecoverable failure so callers own their fallback behavior; (2) `format_inventory()` — compact resource string for prompt injection; (3) `get_completion_kwargs()` — per-provider kwarg lookup for S04 format ablation callers.

This task is pure utility — no LLM calls, no game state, no circular dependencies. The parser is the key correctness item: it must handle all 5 input cases from the research notes, and must return `None` (not a fallback dict) on truncation so test_prompts.py can assert on that specific case.

## Steps

1. Create `src/prompts/json_utils.py` with the following:
   - Import `strip_md` from `src.simulation.llm_router` (do not copy it)
   - Import `PROVIDER_KWARGS` from `src.simulation.llm_router` for `get_completion_kwargs()`
   - Implement `format_inventory(inv: dict[str, int]) -> str` — maps resource names to initials (W=wood, S=stone, G=grain, C=clay, F=fiber) and emits compact `W2 S3 G4 C1 F0` format. Use a fixed ordering (W S G C F) so output is deterministic.
   - Implement `strip_think(text: str) -> str` — removes `<think>...</think>` prefix using regex; handles multiline think blocks with `re.DOTALL`.
   - Implement `extract_first_json_object(text: str) -> str | None` — bracket-counter scan: find first `{`, count `{`/`}` as you scan, return substring when count hits 0. Do NOT use `re.search(r'\{.*\}', ...)` (captures wrong span on multi-fragment strings).
   - Implement `parse_agent_response(raw: str, schema: dict) -> dict | None` with the 4-strategy chain:
     1. `strip_md(raw)` then `json.loads()` — direct parse after fence strip
     2. `strip_think(stripped)` then `json.loads()` — handles DeepSeek `<think>` prefix
     3. `extract_first_json_object(text)` then `json.loads()` — handles JSON embedded in surrounding text
     4. Return `None` — truncated or unrecoverable
   - Log at `logging.WARNING` for each fallback strategy used (not strategy 1 — only log when falling back). Include the first 80 chars of raw input in the log message for diagnosability.
   - Catch only `json.JSONDecodeError`, `ValueError`, `TypeError`. Let any other exception propagate (regex bugs should surface).
   - Implement `get_completion_kwargs(model_family: str) -> dict` — return a shallow copy of `PROVIDER_KWARGS[model_family]`. Raises `KeyError` if family not in registry (don't swallow missing-family errors).

2. Update `src/prompts/__init__.py` to export the public API: `parse_agent_response`, `format_inventory`, `get_completion_kwargs`.

3. Verify the module is importable and spot-check all 3 exports:
   ```
   python -c "
   from src.prompts.json_utils import parse_agent_response, format_inventory, get_completion_kwargs
   # Valid JSON
   assert parse_agent_response('{\"action_type\": \"hoard\"}', {}) == {'action_type': 'hoard'}
   # Fenced JSON
   assert parse_agent_response('\`\`\`json\n{\"action_type\": \"build\"}\n\`\`\`', {}) == {'action_type': 'build'}
   # Truncated → None
   assert parse_agent_response('{\"action_type\": \"bu', {}) is None
   # Think prefix
   assert parse_agent_response('<think>r</think>\n{\"action_type\": \"hoard\"}', {}) == {'action_type': 'hoard'}
   # format_inventory
   assert format_inventory({'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}) == 'W2 S3 G4 C1 F0'
   # get_completion_kwargs - gemini must not have response_format
   kwargs = get_completion_kwargs('gemini')
   assert 'response_format' not in kwargs
   print('T01 ok')
   "
   ```

## Must-Haves

- [ ] `parse_agent_response` returns `None` for truncated JSON (not a fallback dict)
- [ ] `parse_agent_response` returns parsed dict for all 4 recoverable cases
- [ ] Bracket-counter `extract_first_json_object` used — not `re.search(r'\{.*\}', ...)`
- [ ] Only `json.JSONDecodeError`, `ValueError`, `TypeError` caught — no bare `except Exception`
- [ ] `strip_md` imported from `llm_router`, not copied
- [ ] `get_completion_kwargs('gemini')` does not contain `response_format`
- [ ] `format_inventory` uses fixed W S G C F ordering; output is deterministic

## Verification

```bash
cd /Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family
source .venv/bin/activate
python -c "from src.prompts.json_utils import parse_agent_response, format_inventory, get_completion_kwargs; assert parse_agent_response('{\"a\":1}', {}) == {'a': 1}; assert parse_agent_response('{\"a\": \"b', {}) is None; print('ok')"
```

## Inputs

- `src/simulation/llm_router.py` — `strip_md()` and `PROVIDER_KWARGS` to import (not copy)
- S03-RESEARCH.md §"What parse_agent_response() must handle" — 5 input case table
- S03-RESEARCH.md §"Common Pitfalls" — bracket-counter warning, exception scope warning

## Expected Output

- `src/prompts/json_utils.py` — tolerant parser + format_inventory + get_completion_kwargs
- `src/prompts/__init__.py` — updated with public exports
