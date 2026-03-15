---
estimated_steps: 7
estimated_files: 2
---

# T03: Write agent.py and gm.py with double-spend-safe resolution

**Slice:** S02 — Trade Island Engine
**Milestone:** M001

## Description

Implement the two behavioral components: `Agent` (wraps `call_llm`, manages inventory/VP/memory, reflects on round-5 multiples) and `GM` (validates trades sequentially against a working inventory copy to prevent double-spend). The GM double-spend logic is the highest-risk correctness item in the slice — it gets a dedicated inline test before `game.py` ever touches it. Reflection timing (after `round_end`) is enforced by design: `reflect()` is a standalone method that `game.py` calls only after flushing `round_end`.

## Steps

1. Write `src/simulation/agent.py` — `Agent` dataclass fields: `agent_id: str`, `model_family: str`, `model_string: str`, `provider: str`, `inventory: dict[str, int]`, `vp: int = 0`, `memory: list[str] = []`, `buildings_built: list[str] = []`. Methods:
   - `act(round_num: int, game_state: dict, mock_response: str = None) -> dict`: calls `call_llm`, parses JSON response. Expected JSON: `{"action_type": "trade"|"build"|"hoard", "target": str|None, "give": {res: qty}|None, "want": {res: qty}|None, "building": str|None}`. On parse failure, return `{"action_type": "hoard"}` as safe fallback.
   - `respond_to_trade(proposal: dict, game_state: dict, mock_response: str = None) -> dict`: returns `{"accepted": bool, "counter": dict|None}`.
   - `reflect(round_num: int, game_state: dict, mock_response: str = None) -> str`: calls `call_llm(is_reflection=True)`, appends returned text to `self.memory`, returns summary. Only called by `game.py` on rounds 5/10/15/20/25 *after* `round_end` is logged — add docstring: `"Must be called after round_end event is written. See game.py for call site."`

2. Write `src/simulation/gm.py` — imports `call_llm`, `GameLogger`. `GM(model_string: str, logger: GameLogger)`. Implement `resolve_trades(round_num: int, proposals: list[dict], inventories: dict, model_families: dict, config_name: str, mock_response: str = None) -> list[dict]`:
   - Build a **working copy** of inventories: `working_inv = {a: dict(inv) for a, inv in inventories.items()}`.
   - For each proposal in order (sequential, not parallel): validate against `working_inv` — check proposer has enough `give` resources in `working_inv`, check responder accepted (from proposal's `accepted` field), check responder has enough `counter` resources if counter-offered. If valid, update `working_inv` immediately before processing the next proposal.
   - Construct the batch validation prompt; call `call_llm` for GM verification (Mistral JSON mode). If JSON parse fails on first attempt, retry once with a simplified prompt. If both fail, log `gm_parse_failure` event and return all proposals marked invalid.
   - For each resolved trade, emit `gm_resolution` event via `logger.log()` with all H2 fields: `round, trade_idx, valid, reason, proposer_model, responder_model, pairing, give_resource, want_resource, accepted`. `pairing` = `f"{proposer_model_family}_{responder_model_family}"` or `f"{model_family}_mono"` for monoculture.
   - Return list of resolution dicts.

3. Add `if __name__ == "__main__"` double-spend test in `gm.py`:
   - Create a minimal `GM` instance using `mock_response`.
   - Scenario: agent `a0` has `{"wood": 2, "grain": 5}`. Proposals: (1) a0 gives 2 wood to a1, a1 accepts. (2) a0 gives 2 wood to a2, a2 accepts. Both arrive simultaneously.
   - Call `resolve_trades` with both proposals, mock GM response approving all.
   - Assert: resolution[0].valid is True (first trade accepted).
   - Assert: resolution[1].valid is False (second trade rejected — a0's wood already 0 in working copy).
   - Print `"double-spend guard: ok"`.

4. Run the double-spend test: `python src/simulation/gm.py`. Must print `"double-spend guard: ok"`.

5. Verify both modules import cleanly: `python -c "from src.simulation.agent import Agent; from src.simulation.gm import GM; print('ok')"`.

6. Add doc comment to `Agent.reflect()` making the call-order constraint explicit (cannot be moved before this step — the comment documents the contract).

7. Confirm that `gm_resolution` events include `give_resource` and `want_resource` as single strings (not dicts) — H2 analysis filters on these as column values, not nested structures. Each proposal is one resource type for give and one for want (simplest Trade Island mechanic).

## Must-Haves

- [ ] Double-spend test passes: second trade rejected when proposer's inventory is depleted by first trade
- [ ] `gm_parse_failure` event emitted (with `round`, `attempt`, `raw_response[:500]`) when GM JSON parse fails after 2 retries, and all proposals marked invalid
- [ ] `gm_resolution` events contain all 9 H2 fields: `round, trade_idx, valid, reason, proposer_model, responder_model, pairing, give_resource, want_resource, accepted`
- [ ] `Agent.reflect()` docstring explicitly states it must be called after `round_end` is written
- [ ] `Agent.act()` returns `{"action_type": "hoard"}` on JSON parse failure (safe fallback — no crash)
- [ ] `pairing` field is `"{family_A}_{family_B}"` for pairwise or `"{family}_mono"` for monoculture — no nulls

## Verification

- `python src/simulation/gm.py` prints `"double-spend guard: ok"`
- `python -c "from src.simulation.agent import Agent; from src.simulation.gm import GM; print('ok')"` exits 0
- Code review: `working_inv` is a deep copy before the loop, updated inside the loop (not after all proposals)

## Observability Impact

- Signals added/changed: `gm_parse_failure` event logged to JSONL with `round`, `attempt`, `raw_response` (truncated 500 chars) — gives future agent the raw GM output that failed parsing
- How a future agent inspects this: `grep gm_parse_failure data/raw/*/game.jsonl` surfaces all GM resolution failures; `raw_response` field shows what the model returned
- Failure state exposed: GM parse fallback marks all trades invalid and continues — game never hangs on bad GM output

## Inputs

- `src/simulation/llm_router.py` — `call_llm()` from T02
- `src/simulation/logger.py` — `GameLogger` from T01
- `src/simulation/config.py` — `GameConfig` for `config_name` (used in `pairing` field for mono vs pairwise detection)
- S02-RESEARCH.md pitfall: "GM double-spend: snapshot vs sequential validation" — working copy pattern is the fix

## Expected Output

- `src/simulation/agent.py` — `Agent` class with `act()`, `respond_to_trade()`, `reflect()`
- `src/simulation/gm.py` — `GM` class with `resolve_trades()`; inline double-spend test passes
