# S03: Prompt Templates + JSON Mode Validation

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 4-6 hours
**Requirements:** R003

## Goal

All 6 prompt templates implemented with cache-optimized prefix-first structure. JSON mode enforced per provider. Tolerant fallback parser ready.

## Tasks

### T01: Agent action prompt template (~90 tokens input)
- Implement `src/prompts/agent_action.py`
- Structure: [STATIC prefix] game rules, building recipes, output schema → [SEMI-STATIC] round number → [DYNAMIC] agent inventory, recent events, reflection summary
- Compact notation per blueprint §2.2
- JSON schema: `{"act":"trade|build|wait","target":"a1-a6","give":"[r][n]","want":"[r][n]"}`
- Target: ~90 input tokens, ~40 output tokens

### T02: Trade response prompt template (~60 tokens input)
- Implement `src/prompts/trade_response.py`
- JSON schema: `{"accept":true|false,"counter":null|{"give":"[r][n]","want":"[r][n]"}}`
- Target: ~60 input tokens, ~25 output tokens

### T03: GM resolution prompt template (~120 tokens input)
- Implement `src/prompts/gm_resolution.py`
- Input: list of accepted trades + inventory matrix as compact tuples
- JSON schema: `{"valid":[bool,...],"reason":["ok"|"error description",...]}`
- Target: ~120 input tokens, ~80 output tokens

### T04: Building decision prompt (~70 tokens input)
- Implement `src/prompts/building_decision.py`
- JSON schema: `{"build":"house|provisions|tools|none"}`

### T05: Reflection prompt (~150 tokens input, every 5 rounds)
- Implement `src/prompts/reflection.py`
- Uses agent's OWN model family (not a separate model)
- DeepSeek agents: use deepseek-reasoner for reflection (same per-token cost, richer output)
- Output: ≤100 words, stored as compressed notes for next rounds

### T06: JSON mode enforcement + fallback parser
- Implement `src/prompts/json_utils.py`
- Per-provider JSON mode:
  - Groq: `response_format={"type":"json_schema","json_schema":{"name":"action","schema":{...},"strict":True}}`
  - Gemini: `response_format={"type":"json_object"}` + `thinking_budget=0` via extra_body
  - DeepSeek: `response_format={"type":"json_object"}` + schema in prompt text
  - Mistral: `response_format={"type":"json_object"}` + schema in prompt text
- Tolerant fallback parser: try `json.loads()` first, then regex extraction, then default action (wait)
- Log all parse failures with raw response for debugging

### T07: Token counting validation
- Count actual tokens for each template with realistic inputs
- Verify: agent ~90 in/~40 out, trade response ~60 in/~25 out, GM ~120 in/~80 out, reflection ~150 in/~100 out
- If >20% over target: tighten notation
- Document actual token counts in comments

## Acceptance Criteria

- [ ] All 6 prompt functions implemented and return valid strings
- [ ] JSON mode verified working for each provider (manual test call)
- [ ] Tolerant parser handles: valid JSON, JSON with extra text, truncated JSON, empty response
- [ ] Token counts within 20% of blueprint targets
- [ ] `pytest tests/test_prompts.py` → all pass
- [ ] Gemini thinking mode disabled confirmed (response metadata shows no thinking tokens)

## Notes

- CRITICAL: Gemini thinking budget must be disabled at code layer, not just YAML config. Use `extra_body={"thinking":{"type":"disabled"}}` or equivalent for Gemini 2.5 Flash.
- DeepSeek schema workaround: include full JSON schema as example in the prompt text itself (not API parameter)
- Compact notation: W=Wood, S=Stone, G=Grain, Wo=Wood... wait, check blueprint §2.2 for resource abbreviations exactly
- Resource abbreviations from blueprint: W=Wood, S=Stone, G=Grain, Wo=Wood? Check — blueprint uses W,S,G,Wo,O,C. Clarify during implementation.
