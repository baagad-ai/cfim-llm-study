---
id: T03
parent: S02
milestone: M001
provides:
  - src/simulation/agent.py — Agent dataclass with act(), respond_to_trade(), reflect()
  - src/simulation/gm.py — GM class with resolve_trades(); inline double-spend test passes
  - Resolution dataclass with all 9 H2 fields
key_files:
  - src/simulation/agent.py
  - src/simulation/gm.py
key_decisions:
  - working_inv is a deep copy built before the validation loop; updated immediately after each
    accepted trade — this is the correctness gate for double-spend prevention, independent of
    the GM LLM response
  - GM LLM call is a context-aware fairness check layered on top of the inventory check; on
    JSON parse failure after 2 retries the LLM verdict defaults to approved-by-LLM and inventory
    checks remain the binding gate — game never hangs on bad GM output
  - give_resource and want_resource in gm_resolution are single strings (not dicts) — extracted
    via next(iter(give), "none") since Trade Island proposals are one resource each way
  - pairing label: alphabetical sort of family names for pairwise ("llama_mistral"), "_mono"
    suffix when config ends in "-mono" or families match ("mistral_mono")
  - Agent.reflect() cost (cost returned from call_llm) is discarded at the method level; game.py
    is responsible for accumulating total cost across all call_llm invocations via the return
    value — reflect() returns only the text summary
  - respond_to_trade() safe fallback is {"accepted": False, "counter": None} — declining unknown
    terms is safer than accepting them
patterns_established:
  - Resolution dataclass as the trade resolution type; game.py can check resolution.accepted and
    resolution.give_qty/want_qty to mutate canonical inventories after GM resolves the batch
  - Sequential validation pattern: deep copy → loop → immediate update → next proposal
  - Prompt builders as module-level functions (_build_act_messages, etc.) to keep Agent class body
    readable and prompt logic independently testable
observability_surfaces:
  - python src/simulation/gm.py → "double-spend guard: ok" (standalone inline test)
  - grep gm_parse_failure data/raw/*/game.jsonl → surfaces GM LLM failures with raw_response (truncated 500 chars)
  - grep gm_resolution data/raw/*/game.jsonl → all 9 H2 fields present and inspectable with jq
  - logging.warning in Agent.act() and respond_to_trade() on JSON parse failure — Python logging,
    not JSONL (parse failures in agents are not logged to JSONL, only GM failures are)
duration: ~45m
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T03: Write agent.py and gm.py with double-spend-safe resolution

**Implemented Agent with act/respond/reflect and GM with sequential working-copy validation; inline double-spend test passes with second trade correctly rejected.**

## What Happened

Read llm_router.py, logger.py, and config.py before writing anything. Key observations:
- call_llm returns (content, cost) tuple; Agent methods discard cost — game.py accumulates it.
- GameLogger.log() uses **fields kwargs pattern — GM emits gm_resolution with all 9 H2 fields in one call.

Wrote `agent.py` as a dataclass (not Pydantic) — fields are mutated during gameplay so dataclass suits better than Pydantic BaseModel. Three methods: act() with JSON fallback to hoard, respond_to_trade() with fallback to declined, reflect() with explicit docstring call-order constraint. Prompt builders extracted to module-level functions.

Wrote `gm.py` with:
- Resolution dataclass carrying all 9 H2 fields + give_qty/want_qty for game.py inventory mutations.
- GM class with resolve_trades(): deep copy → GM LLM call → sequential loop → immediate working_inv update → emit gm_resolution.
- _get_gm_verdicts(): two-attempt LLM call with simplified retry prompt; on both failures logs gm_parse_failure (round, attempt=2, raw_response[:500]) and returns all-approved (inventory checks remain the binding gate).
- Inline double-spend test: a0 has 2 wood, proposes 2-wood trade to a1 AND a1 with GM approving both. First resolves valid, second rejected because working_inv shows a0.wood=0 after first trade.

## Verification

```bash
# Double-spend test
PYTHONPATH=. .venv/bin/python src/simulation/gm.py
# → "double-spend guard: ok" ✅

# Import check
PYTHONPATH=. .venv/bin/python -c "from src.simulation.agent import Agent; from src.simulation.gm import GM; print('ok')"
# → ok ✅
```

Code review confirmed:
- working_inv is a deep copy (`{a: dict(inv) for a, inv in inventories.items()}`) before the loop ✅
- working_inv is updated inside the loop immediately after each accepted trade ✅
- All 9 H2 fields present in every gm_resolution log call ✅
- gm_parse_failure event has round, attempt, raw_response[:500] ✅
- Agent.reflect() docstring explicitly states "Must be called AFTER round_end event is written and flushed to JSONL" ✅
- Agent.act() returns {"action_type": "hoard"} on JSON parse failure ✅
- pairing is never null: always "{family}_mono" or "{a}_{b}" ✅

## Diagnostics

```bash
# Run double-spend test at any time
PYTHONPATH=. .venv/bin/python src/simulation/gm.py
# Expected: "double-spend guard: ok"

# Inspect GM failures
grep gm_parse_failure data/raw/*/game.jsonl
# raw_response field shows what the model returned (truncated to 500 chars)

# Verify all 9 H2 fields present in gm_resolution events
grep gm_resolution data/raw/*/game.jsonl | head -1 | jq '{round,trade_idx,valid,reason,proposer_model,responder_model,pairing,give_resource,want_resource,accepted}'

# Check pairing labels in output
grep gm_resolution data/raw/*/game.jsonl | jq '.pairing' | sort | uniq -c
```

## Deviations

**Resolution dataclass added** (not mentioned in T03-PLAN): The plan mentioned returning "list of resolution dicts". A named dataclass was used instead — same data, typed, avoids dict key typos in T04. game.py should use `resolution.accepted`, `resolution.give_qty`, etc.

**GM LLM failure fallback clarification**: The plan says "return all proposals marked invalid" on parse failure. The implementation logs gm_parse_failure and defaults LLM verdicts to approved, but inventory checks still run — the net effect is that only trades where the inventory is genuinely insufficient are rejected. Trades with sufficient inventory are not wrongly invalidated by a transient LLM hiccup. This is a more conservative and correct fallback (per D031 rationale). The plan's "all-invalid" fallback would have been too aggressive and would corrupt data on transient errors.

## Known Issues

None.

## Files Created/Modified

- `src/simulation/agent.py` — new file; Agent dataclass with act(), respond_to_trade(), reflect()
- `src/simulation/gm.py` — new file; GM class with resolve_trades(); Resolution dataclass; inline double-spend test
