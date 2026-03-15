# S03: Prompt Templates + JSON Mode Validation

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 4-6 hours
**Requirements:** R003
**Depends on:** S02 (simulation schema must be confirmed before finalising prompt variables)

## Goal

All 6 prompt templates implemented with cache-optimized prefix-first structure. Per-provider JSON parse strategy validated. Tolerant fallback parser ready. Token counts verified within 20% of blueprint targets.

## Context: Per-Provider JSON Strategy (confirmed in S01)

| Provider | JSON Mode | Approach |
|---|---|---|
| Groq | `response_format={'type':'json_object'}` | Native enforcement ✅ |
| OpenRouter/DeepSeek | `response_format={'type':'json_object'}` | Native enforcement via OpenRouter ✅ |
| Gemini | ❌ No json_object mode | Strip markdown fences, then `json.loads()` |
| Mistral | `response_format={'type':'json_object'}` | Native enforcement ✅ |

Fallback parser needed for all models for edge cases (<1% expected).

## Resource Abbreviations (from blueprint §2.2, confirmed)

`W`=Wood, `S`=Stone, `G`=Grain, `Wo`=Wool, `O`=Ore, `C`=Clay

Building recipes: House(W2+S2→3VP), Provisions(G2+Wo2→3VP), Tools(O2+C2→3VP)

## Tasks

### T01: Agent action prompt (~90 tokens input)
File: `src/prompts/agent_action.py`

```
[STATIC PREFIX — cached]
TRADE ISLAND RULES | 6 agents, 25 rounds, first to 12VP wins.
BUILD: House(W2+S2=3vp) Prov(G2+Wo2=3vp) Tools(O2+C2=3vp)
Eat 1G/rnd. 0G=damage.
Output JSON: {"act":"trade|build|wait","target":"a1-a6","give":"[r][n]","want":"[r][n]"}

[SEMI-STATIC — changes once per round]
R{round}/25

[DYNAMIC — changes every call]
You:A{id} Specialty:{res} | VP:{vp}/12
INV: W{w} S{s} G{g} Wo{wo} O{o} C{c}
Recent: {last_3_events_compressed}
Notes: {reflection_summary_compressed}
```
Target: ~90 input tokens, ~40 output tokens
JSON schema: `{"act":"trade|build|wait","target":"a1-a6","give":"[r][n]","want":"[r][n]"}`

### T02: Trade response prompt (~60 tokens input)
File: `src/prompts/trade_response.py`

```
[STATIC PREFIX — cached]
TRADE ISLAND | Accept/counter/reject trades.
Output JSON: {"accept":true|false,"counter":null|{"give":"[r][n]","want":"[r][n]"}}

[DYNAMIC]
A{proposer} offers you {give_res}{give_n} for your {want_res}{want_n}.
Your INV: W{w} S{s} G{g} Wo{wo} O{o} C{c} | VP:{vp}/12 R{round}/25
```
Target: ~60 input tokens, ~25 output tokens

### T03: GM resolution prompt (~120 tokens input)
File: `src/prompts/gm_resolution.py`

```
[STATIC PREFIX — cached]
TRADE ISLAND GM | Validate trades. Check sufficient resources, no double-spending.
Output JSON: {"valid":[bool,...],"reason":["ok"|"error description",...]}

[DYNAMIC]
RESOLVE TRADES R{round}:
{list_of_accepted_trades_as_compact_tuples}
Current inventories: {agent_inventory_matrix}
```
Target: ~120 input tokens, ~80 output tokens

### T04: Building decision prompt (~70 tokens input)
File: `src/prompts/building_decision.py`

```
[STATIC PREFIX — cached]
TRADE ISLAND | Choose what to build this round or wait.
Output JSON: {"build":"house|provisions|tools|none"}
BUILD: House(W2+S2=3vp) Prov(G2+Wo2=3vp) Tools(O2+C2=3vp)

[DYNAMIC]
R{round}/25 | A{id} VP:{vp}/12
INV: W{w} S{s} G{g} Wo{wo} O{o} C{c}
```
Target: ~70 input tokens, ~15 output tokens

### T05: Reflection prompt (~150 tokens input, every 5 rounds)
File: `src/prompts/reflection.py`

```
You are A{id} on Trade Island. Summary of rounds {start}-{end}:
{compressed_event_log}
Your current position: VP:{vp} INV:{inventory}
Analyze: Who trades fairly? Who hoards? What's scarce? Your best strategy going forward?
Keep under 100 words.
```
- Uses agent's **own** model family (not a separate model)
- DeepSeek agents: use `openrouter/deepseek/deepseek-r1` for reflection (richer, same cost)
- DeepSeek-R1 response: strip `<think>...</think>` block, use only the final answer
- Target: ~150 input tokens, ~100 output tokens

### T06: JSON parse utilities (`src/prompts/json_utils.py`)

```python
def parse_agent_response(raw: str, schema: str) -> dict | None:
    """
    Tolerant JSON parser. Try in order:
    1. json.loads(raw.strip())
    2. Strip markdown fences, json.loads()
    3. Regex: find first {...} substring, json.loads()
    4. Return None (caller uses default action: wait)
    Log all failures with raw response for debugging.
    """

def get_completion_kwargs(model_family: str) -> dict:
    """
    Return the correct litellm kwargs for each model family.
    Gemini: thinking={'type':'disabled','budget_tokens':0}, max_tokens=200, NO response_format
    Others: response_format={'type':'json_object'}, max_tokens=150
    """
```

### T07: Token count validation
- Render each template with realistic inputs
- Count tokens: `litellm.token_counter(model=..., messages=[...])`
- Verify within 20% of targets
- Document actual counts in docstrings

## Acceptance Criteria

- [ ] All 6 prompt functions implemented, return valid strings
- [ ] `parse_agent_response` handles: valid JSON, JSON with fences, JSON with extra text, truncated JSON, empty string
- [ ] `get_completion_kwargs` returns correct per-model kwargs (Gemini gets `thinking`, not `response_format`)
- [ ] Token counts within 20% of blueprint targets
- [ ] `pytest tests/test_prompts.py` passes
- [ ] Gemini responses with fences are correctly parsed (tested with real calls)
- [ ] DeepSeek-R1 reflection: `<think>` block stripped correctly

## Notes

- Do NOT call any provider in this slice except for token counting (trivial cost)
- Format validation (90% parse rate threshold) happens in S04, not here
- The static prefix must be byte-for-byte identical across all calls of the same type for cache hits
