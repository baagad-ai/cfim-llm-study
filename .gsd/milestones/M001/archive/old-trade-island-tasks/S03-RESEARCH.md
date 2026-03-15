# S03: Prompt Templates + Tolerant Parser — Research

**Date:** 2026-03-15
**Scope:** `src/prompts/` (6 modules), `tests/test_prompts.py`, `GameConfig.from_name('phase0')` update, `agent.py`/`gm.py` prompt builder replacement

---

## Summary

S03 has three distinct jobs, and it's worth understanding them as separate problems before touching code:

**Job 1 — Move and compress the prompt builders.** The prompt building logic already exists inside `agent.py` (`_build_act_messages`, `_build_respond_messages`, `_build_reflect_messages`) and `gm.py` (`_build_gm_prompt`, `_build_simple_gm_prompt`). These are inlined module-level functions. S03 extracts them into `src/prompts/` modules — but extraction alone isn't enough. The current prompts are 2.5–3.8× over blueprint token targets (`act`: ~260 tok vs 90-tok target; `respond_to_trade`: ~227 tok vs 60-tok target). They dump the full `game_state` JSON dict into the user message, which is almost entirely dynamic content — killing cache hits. The static system messages need to become long stable prefixes that carry all rules, building recipes, and JSON schemas. The user messages need to become short dynamic tails (round, inventory, VP).

**Job 2 — Fix the tolerant parser.** `agent.py` currently calls `json.loads(content)` directly with a broad `except` that falls back to `{"action_type": "hoard"}` or `{"accepted": False}`. `strip_md()` from `llm_router.py` handles fence stripping before the parse but misses three cases: JSON embedded in surrounding text, truncated JSON (from `max_tokens` cutoff), and DeepSeek R1's occasional `<think>...</think>` prefix in V3.2 chat output. `json_utils.py` must implement `parse_agent_response(raw, schema)` with a multi-strategy fallback: direct parse → strip-think + parse → extract-first-json-block + parse → return `None`. The `None` return (not a fallback value) is the key contract: callers decide what to do on None, which gives test_prompts.py a clean assertion surface.

**Job 3 — Fix the phase0 config and respond_to_trade template.** `GameConfig.from_name('phase0')` currently returns mistral-mono with `config_name="phase0"`. S03 must update it to a real 4-family mix. The natural assignment for a 6-agent game is 2 Llama + 2 DeepSeek + 1 Gemini + 1 Mistral (2:2:1:1 balance, all families represented). The respond_to_trade template is the behaviorally critical fix: all 115 trade proposals in the Mistral-mono run were declined (D037). The current prompt gives agents no strategic reason to accept — it frames the choice as binary accept/decline without explaining that resources block buildings. The new template must frame trades as VP-unlocking moves.

**Primary recommendation:** Implement in task order — (1) json_utils.py with full parse fallback chain, (2) the 5 prompt modules extracting from agent.py/gm.py and compressing toward token targets, (3) wire agent.py + gm.py to import from src/prompts/, (4) update phase0 config, (5) write test_prompts.py. The wiring step (3) is the integration risk — test_smoke.py must still pass 5/5 after the swap.

---

## Recommendation

**Architecture:** `src/prompts/` is a pure-function module layer. Functions take typed arguments (agent state, game state dicts) and return `list[dict]` (chat messages). No class state, no LLM calls inside prompt modules. The `json_utils.py` module is the exception — it implements the parse fallback chain used by callers after they get raw LLM content.

**Token budget strategy:** Put all game rules, building costs, JSON schema in the `system` message (static, cache-able). Put round, inventory, recent events in the `user` message (dynamic, 3–5 lines max). Never dump the full `game_state` dict into user message — it's mostly agent VP data that changes every round and breaks cache hit rates. VP leaderboard can be 2-3 compressed lines (`a0:6vp a1:3vp a2:3vp`).

**respond_to_trade fix:** Rewrite the system prompt to explain WHY trading is strategically valuable. Key additions: (1) "Trading unlocks buildings you can't afford alone", (2) "If they have what you need, a fair trade gets you closer to building", (3) "Counter-proposing a different trade is always better than flat declining". The current prompt is pure mechanism description with no strategic framing — agents rationally default to "no" when uncertain.

**phase0 config:** 2 Llama + 2 DeepSeek + 1 Gemini + 1 Mistral = 6 agents. Agents a0–a1 → llama, a2–a3 → deepseek, a4 → gemini, a5 → mistral. This is a `_mixed_4family()` builder in `GameConfig`, invoked by `from_name('phase0')`. It gives all 4 families participation in every calibration game and satisfies the S04 "all 4 providers route correctly" success criterion in a single game.

**Integration:** Replace `_build_*_messages()` in `agent.py` and `_build_gm_prompt()` / `_build_simple_gm_prompt()` in `gm.py` with `from src.prompts.<module> import build_<type>_messages`. The existing function signatures and return types are unchanged — only the implementation moves. `test_smoke.py` must continue to pass 5/5 after this swap; that's the integration gate before writing `test_prompts.py`.

---

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| JSON fence stripping | `strip_md()` in `src/simulation/llm_router.py` | Already handles `` ```json `` and bare `` ``` `` fences. Import directly into `json_utils.py` — do not copy. |
| Per-provider LLM kwargs | `PROVIDER_KWARGS` dict in `src/simulation/llm_router.py` | `get_completion_kwargs(model_family)` can just look up this dict. No new kwarg logic needed. |
| Mock LLM calls in tests | `mock_response=` kwarg in `call_llm()` | All `test_prompts.py` tests should pass mock strings as raw content — no real API calls. |
| Schema validation | Pydantic v2 (already installed) | `GameConfig` uses it. If prompt response schemas need validation, use Pydantic models. But `parse_agent_response(raw, schema)` can just return a dict — Pydantic is optional overhead here. |
| Retry on parse failure | `tenacity` (installed) — but DON'T use for parse retries | Application-level parse retry belongs in the caller (agent.py act()), not inside `parse_agent_response()`. Keep the parser a pure function; retry orchestration stays in the caller. |

---

## Existing Code and Patterns

- `src/simulation/agent.py` — Contains `_build_act_messages()`, `_build_respond_messages()`, `_build_reflect_messages()`. These are the **source** for `src/prompts/{agent_action,trade_response,reflection}.py`. Extract verbatim, then compress. Do not modify behavior before extracting — extract first, test smoke, then compress.
- `src/simulation/gm.py` — Contains `_build_gm_prompt()` and `_build_simple_gm_prompt()`. These are the source for `src/prompts/gm_resolution.py`. The two-attempt retry structure in `_get_gm_verdicts()` stays in `gm.py`; only the prompt text moves to `src/prompts/`.
- `src/simulation/llm_router.py` — `strip_md()` is the fence stripper; import it into `json_utils.py` (don't copy). `PROVIDER_KWARGS` is the per-provider kwarg map; `get_completion_kwargs()` can return from it. `call_llm()` already applies these per call — `get_completion_kwargs()` is for S04 format-ablation callers that need to inspect kwargs without making a call.
- `src/simulation/config.py` — `_MODEL_REGISTRY` defines the 4 family entries. The phase0 builder (`_mixed_4family()`) uses `_make_agent_entry()` directly. Pattern to follow: same as `_pairwise()` builder — list comprehension, `_make_agent_entry(f"a{i}", family)`.
- `tests/test_smoke.py` — **Must still pass 5/5 after S03 integration.** Run it as the integration gate before writing `test_prompts.py`. If it fails, stop and fix wiring before proceeding.
- `data/raw/1e8788dd/game.jsonl` — Real Mistral-mono game data. Action distribution: 35 builds, 115 trade proposals, 0 accepted trades. The `gm_resolution` reasons are: `responder_declined` (78), `responder_insufficient_wood` (33), 4 edge cases. This is the baseline to beat with the new respond_to_trade prompt.
- `scripts/test_connectivity.py` — `strip_md()` pattern originated here. Per-provider kwargs also match what's in `llm_router.py`. No need to read again — `llm_router.py` is the authoritative copy.

---

## Constraints

- **Field names must match locked JSONL schema.** Prompt variables that reference agent data must use exact field names: `agent_id`, `model_family`, `round`, `vp`, `game_id`. Any aliasing in prompt text is cosmetic only — the variable names passed in must match what `GameLogger.log_round_end()` emits.
- **Static prefix must be byte-for-byte identical across same call type.** The `system` message content for all `agent_action` calls must be exactly identical regardless of agent, round, or game state. Any agent-specific or round-specific data in the system message destroys caching. Dynamic content lives only in the `user` message.
- **Gemini does not use JSON mode (D021).** `get_completion_kwargs()` must NOT return `response_format` for the gemini provider. Gemini relies on `strip_md()` + tolerant parser. Current `PROVIDER_KWARGS["gemini"]` already excludes `response_format` — preserve this.
- **DeepSeek R1 reflection output is free-form.** The `reflect()` call with `is_reflection=True` switches to R1 for DeepSeek agents. R1 output may contain `<think>...</think>` blocks. The reflection text is stored as-is in `agent.memory` — it's never JSON-parsed. `strip_think()` is only needed if callers want clean text for memory injection into subsequent prompts. The JSONL `reflection.summary` field already truncates to 500 chars.
- **Building decision is NOT a separate LLM call.** The blueprint §2.6 lists "building decisions" as a separate row in the token budget, but S02's implementation merged it into `act()` — the action response includes both `action_type: build` and `building: <name>`. Do NOT split this into a separate call; that would require game.py changes and break test_smoke.py. The `building_decision.py` module should contain helper functions (e.g., `format_building_options()`) used by `agent_action.py` to render the building list in compact format. It does not build or make separate LLM calls.
- **`parse_agent_response()` must return None on truncated/unrecoverable JSON.** The caller (agent.py) decides the fallback (hoard/decline). Returning a fallback dict from inside the parser hides failures from the caller and prevents test assertions from catching the truncated-JSON case explicitly.
- **`test_smoke.py` 5/5 is a hard gate.** Do not advance to writing `test_prompts.py` until `pytest tests/test_smoke.py -v` shows 5 passed.
- **`20% tolerance` on token count targets.** Ranges: act [72–108 tok], respond_to_trade [48–72 tok], reflection [120–180 tok], GM [96–144 tok]. Rough estimate: chars/4 ≈ tokens. Current act at ~260 tok needs to drop to ≤108 tok — requires aggressive compression.
- **No polars/analysis imports in `test_prompts.py`.** Same constraint as `test_smoke.py` — only `src/simulation/` and `src/prompts/` imports.

---

## Common Pitfalls

- **Extracting prompt builders before compressing them.** Extract → verify smoke passes → then compress. Compressing while extracting doubles the failure surface: if smoke fails, you don't know if the extraction or the compression broke it.
- **Putting dynamic data in the system message.** Anything that changes per round/agent (inventory, VP, round number) in the system message breaks cache hits. The system message must contain only things that never change within a call type: game rules, building costs, resource list, JSON schema.
- **`json.dumps(inventory)` in compact format.** The verbose `{"wood": 2, "stone": 3}` is 8+ tokens. The compact `W2 S3 G4 C1 F2` is 3 tokens (1 per resource). Blueprint §2.2 uses this compact format — implement `format_inventory(inv: dict) -> str` in `json_utils.py` and use it in all prompt modules.
- **`parse_agent_response` catching all exceptions.** Catch only `json.JSONDecodeError`, `ValueError`, `TypeError`. A bare `except Exception` swallows bugs in the extraction regex itself — those should propagate so tests catch them.
- **Overwriting `agent.py`'s JSON parse without updating the fallback value.** The current fallback for `act()` is `{"action_type": "hoard"}`. The new `parse_agent_response()` returns `None` on failure — callers must add `if result is None: return {"action_type": "hoard"}` explicitly. The fallback must not move inside the parser.
- **Using `re.search(r'\{.*\}', text, re.DOTALL)` for JSON extraction.** This matches the outer braces but captures everything between the first `{` and last `}` in the string, which on a long string with multiple JSON fragments gives wrong output. Use `re.search(r'\{[^{}]*\}', text)` for simple single-level JSON, or better: scan for the first `{`, then find its matching `}` with a bracket counter. The bracket-counter approach handles nested dicts correctly.
- **Token count verification with `len(text) // 4`.** The chars/4 estimate is rough — actual tokenization for GPT/Mistral BPE is typically 1 token per 3.5–4.5 chars depending on vocabulary. For verification purposes, use the estimate but note in test comments that ±20% tolerance absorbs the estimation error.
- **`phase0` config returning a fixed 4-family mix that's never varied.** Phase 0 has 30 calibration games with various configs — monoculture per family, pairwise, etc. `from_name('phase0')` returns ONE representative config (the 4-family mixed game). S04 will call `from_name('mistral-mono')`, `from_name('llama-mono')`, `from_name('pairwise-llama-gemini')` etc. separately. The `phase0` config is specifically for verifying all-4-families routing in a single game.
- **"llama-mono" not being a registered config.** `_MODEL_REGISTRY` has `llama` but `from_name()` only handles `mistral-mono` explicitly. S04 will need `llama-mono`, `deepseek-mono`, `gemini-mono`. These are trivially built with `_mistral_mono`'s pattern — but S03 should add them or leave a clear comment that S04 must add them. Adding now is low-risk (5 lines) and prevents S04 from getting blocked on a missing config.

---

## Open Risks

- **Trade acceptance rate may remain ~0% even with improved respond_to_trade prompt.** The D037 behavioral finding may be architecture-specific to Mistral Small — agents prefer the certainty of building over the uncertainty of trading. The improved prompt should raise acceptance rates but won't guarantee >0 in Phase 0. S04 calibration is the validation gate (S03 is measured by prompt design quality, not live acceptance rate).
- **Token compression may degrade JSON parse quality.** The blueprint's ultra-compact format (`W2 S3 G4 Wo2 O0 C1`) uses resource abbreviations not seen in training data context. Models may misinterpret compressed prompts and produce malformed JSON at higher rates than the verbose form. The S04 format ablation test (80 calls) is designed to catch this — but if compact prompts fail at >10% rate on any model, S04 will need to fall back to verbose, which voids S03's token savings.
- **`get_completion_kwargs(model_family)` vs provider key.** Current `PROVIDER_KWARGS` is keyed by provider string (`"mistral"`, `"groq"`, `"gemini"`, `"deepseek"`). `model_family` in `GameConfig` uses the same strings. No mismatch risk for the 4 current families — but the mapping assumption should be documented explicitly in `json_utils.py`.
- **`test_smoke.py` mock_response coupling to prompt format.** `test_smoke.py` passes `_MOCK_ACT_HOARD` and `_MOCK_ACT_TRADE` as mock responses — these are valid JSON action dicts. As long as the new prompt modules produce the same JSON schema expectations (same keys, same types), mock responses remain valid. If S03 changes the expected response schema (e.g., renames `action_type` to `act`), test_smoke.py mock strings will need updating. Keep the JSON schema stable — only compress the prose, not the key names.
- **Static prefix byte-for-byte identity across litellm versions.** Cache hits require exact byte match of the prefix. If litellm or any middleware normalizes whitespace or adds metadata to messages before caching, the "identical system message" guarantee is weakened. This is a litellm internal — not directly testable in unit tests. Document as known caveat; Phase 0 cache hit rates will reveal if caching is actually working.

---

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| Python prompt engineering | No specific skill needed | none found |
| LiteLLM | No dedicated skill installed | none found |
| pytest | Standard — no skill needed | built-in |

---

## Appendix: Key Measurements

### Current token counts (estimated chars/4, realistic game state):

| Prompt | Current est. | Blueprint target | Over by | 20% range |
|--------|-------------|-----------------|---------|-----------|
| `act` (agent_action) | ~260 tok | ~90 tok | 2.9× | 72–108 |
| `respond_to_trade` | ~227 tok | ~60 tok | 3.8× | 48–72 |
| `reflect` | ~215 tok | ~150 tok | 1.4× | 120–180 |
| `gm_resolution` | ~90 tok | ~120 tok | 0.75× (under) | 96–144 |

Reflection is within 20% tolerance as-is. GM is under-target. `act` and `respond_to_trade` need aggressive compression.

### D037 rejection breakdown (115 proposals, real Mistral-mono run):

| Reason | Count |
|--------|-------|
| responder_declined (LLM chose no) | 78 (68%) |
| responder_insufficient_wood | 33 (29%) |
| GM/other | 4 (3%) |

The 29% `insufficient_wood` failures are correct behavior — agents who don't have the resource can't trade it. The 68% pure LLM declines are the behavioral fix target. A well-incentivized respond_to_trade prompt should reduce this to <40% (agents decline when trade is genuinely bad, not reflexively).

### What `parse_agent_response()` must handle:

| Case | Input example | Expected output |
|------|--------------|-----------------|
| Valid JSON | `'{"action_type": "build"}'` | Parsed dict |
| Fenced JSON | `` ```json\n{"action_type":"build"}\n``` `` | Parsed dict |
| JSON + surrounding text | `'Here is my action: {"action_type":"build"} done.'` | Parsed dict |
| Truncated JSON | `'{"action_type": "bu'` | `None` |
| DeepSeek think + JSON | `'<think>reasoning</think>\n{"action_type":"build"}'` | Parsed dict |

---

## Sources

- `src/simulation/agent.py` — current inline prompt builders; `act()`, `respond_to_trade()`, `reflect()` call signatures
- `src/simulation/gm.py` — current GM prompt builders; `_get_gm_verdicts()` two-attempt retry structure
- `src/simulation/llm_router.py` — `strip_md()`, `PROVIDER_KWARGS`, `call_llm()` signatures
- `src/simulation/config.py` — `_MODEL_REGISTRY`, `_make_agent_entry()`, `from_name()` factory pattern
- `data/raw/1e8788dd/game.jsonl` — real Mistral-mono run; action distribution, rejection reasons for D037 diagnosis
- `research_blueprint_v6.md §2.2–2.5` — blueprint compact prompt templates and token targets
- `research_blueprint_v6.md §2.6` — per-round token budget table (building_decision as separate row)
- `.gsd/DECISIONS.md D021` — Gemini: no JSON mode, use fence stripper
- `.gsd/DECISIONS.md D024` — DeepSeek R1 for reflection only; V3.2 for all action calls
- `.gsd/DECISIONS.md D037` — 0 accepted trades in Mistral-mono real run; behavioral root cause
- `tests/test_smoke.py` — mock response format and integration gate requirements
