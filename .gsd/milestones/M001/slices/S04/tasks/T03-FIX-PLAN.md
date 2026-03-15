---
estimated_steps: 28
estimated_files: 10
---

# T03-FIX: Simulation Repair Sprint

**Slice:** S04 — Phase 0 Calibration (30 games)
**Milestone:** M001
**Status:** ⬜ Not started

## Context

MASTER_AUDIT_2026-03-15 identified 8 critical failures (CF1–CF8), 10 should-fix issues (SF1–SF10), and 7 nice-to-have items (NH1–NH7) that collectively make the simulation scientifically invalid. All agents currently end at −17 to −20 VP (starvation floor) with 0% trade acceptance across 300+ proposals. H1–H4 are untestable on this data.

This task resolves all issues. Execution order follows the audit's recommendation: mechanics first, then prompts, then engineering, then observability, then tests.

---

## Issue Register

### Must Fix (CF = Critical Failure) — blocks data collection

| ID | Layer | Issue | Est |
|---|---|---|---|
| CF1 | Mechanics | No grain income → starvation dominates from round 6 | 30m |
| CF2 | Mechanics | All agents start identical → no trade incentive | 1h |
| CF3 | Mechanics | Granary building effect not implemented (+2 grain/round) | 30m |
| CF4 | Prompts | Trade response has no urgency (grain_rounds_left, survival framing) | 1h |
| CF5 | Prompts | Act prompt has no grain urgency or others' grain visibility | 1h |
| CF6 | Prompts | Reflection prompt hallucinates game elements (no game context) | 30m |
| CF7 | Engineering | Resource key normalization missing (W/S/G/C/F silently miss inventory) | 30m |
| CF8 | Engineering | Counter-offer double-deduction (grain deducted twice from responder) | 30m |

### Should Fix (SF) — before 30-game run

| ID | Layer | Issue | Est |
|---|---|---|---|
| SF1 | Prompts | Memory is raw prose ~200 chars × 3 = too long for token budget | 1h |
| SF2 | Prompts | No public inventory visibility in act prompt | 30m |
| SF3 | Engineering | Pairing label wrong for phase0 config (is_mono logic) | 5m |
| SF4 | Observability | No `raw_action` field in agent_action events | 15m |
| SF5 | Observability | No `build_failed` event with reason | 15m |
| SF6 | Observability | No `inventory` dict in round_end events | 15m |
| SF7 | Tests | Token budget test assertion is stale (108 → 160) | 5m |
| SF8 | Mechanics | Early-win check (12VP) not implemented | 15m |
| SF9 | Mechanics | Hoard is a no-op (no resource gain) | 30m |
| SF10 | Engineering | `time.sleep(0.1)` should be 0.5s (Gemini rate limit safety) | 2m |

### Nice to Have (NH) — include in this sprint

| ID | Layer | Issue | Est |
|---|---|---|---|
| NH1 | Reproducibility | `requirements-lock.txt` missing | 5m |
| NH2 | Reproducibility | `.env.example` missing | 10m |
| NH3 | Reproducibility | Seed not wired to actual RNG | 30m |
| NH4 | Science | Model version not logged from API response | 30m |
| NH5 | Science | DeepSeek R1 reflection behavioral split undocumented | 15m |
| NH6 | Paper | Related work section missing 2025–2026 papers | 1h |
| NH7 | Tests | 9 missing unit tests for mechanics | 2h |

---

## Steps

### Phase 1 — Game Mechanics (CF1–CF3, SF8–SF9)

**Step 1: Add grain_income field to GameConfig (CF1)**
- File: `src/simulation/config.py`
- Add `grain_income: int = 1` to `GameConfig` dataclass/Pydantic model.
- This is the base grain income per round per agent. Set default to 1 so net grain is flat (1 income − 1 consumption = 0 net). Survival is now possible.

**Step 2: Apply grain income in game loop (CF1)**
- File: `src/simulation/game.py`
- In the round loop, before grain consumption, add:
  ```python
  # Apply base grain income
  for agent in agents:
      agent.inventory['grain'] = agent.inventory.get('grain', 0) + config.grain_income
  ```
- After Granary build tracking (Step 4), also apply Granary bonus for owners.

**Step 3: Implement resource specialization (CF2)**
- File: `src/simulation/config.py`
- Define 6 specialty archetypes as a constant:
  ```python
  SPECIALTY_ARCHETYPES = [
      {"wood": +3, "clay": -2},    # a0: wood-rich
      {"stone": +3, "wood": -2},   # a1: stone-rich
      {"grain": +3, "stone": -2},  # a2: grain-rich
      {"clay": +3, "grain": -2},   # a3: clay-rich
      {"fiber": +3, "clay": -2},   # a4: fiber-rich
      {"wood": +2, "fiber": -2},   # a5: wood-secondary
  ]
  ```
- Add `resource_specialization: bool = True` to GameConfig.
- When building starting inventories, if `resource_specialization` is True, apply the archetypes (rotated by round-seeded RNG so order varies per game). Record which agent got which archetype in `game_start` event under `specialty_assignments`.
- Ensure no inventory value goes below 1 after applying deltas (floor at 1).
- Add `specialty: str` field to Agent (the name of their specialty resource, e.g., "wood").

**Step 4: Implement Granary building effect (CF3)**
- File: `src/simulation/game.py`
- Add `granary_owners: set[str]` to game state (initialized as empty set).
- After any successful Granary build: `granary_owners.add(agent_id)`.
- Each round, after base grain income, before consumption: for each agent in `granary_owners`, apply `+2` grain.
- Verify in test: build Granary at round 1, check agent has base+2 grain income each round thereafter.

**Step 5: Implement early-win check (SF8)**
- File: `src/simulation/game.py`
- After the build phase, check: `if any(a.vp >= 12 for a in agents): break`
- Log a `game_over` event with `reason: "vp_target_reached"` and the winning agent_id.

**Step 6: Implement hoard gives +1 specialty resource (SF9)**
- File: `src/simulation/game.py`
- When action_type is "hoard": `agent.inventory[agent.specialty] = agent.inventory.get(agent.specialty, 0) + 1`
- Log a `hoard` event with agent_id and specialty resource gained.

---

### Phase 2 — Prompts (CF4–CF6, SF1–SF2)

**Step 7: Rewrite trade response prompt (CF4)**
- File: `src/prompts/trade_response.py`
- New system message (inject `grain_rounds_left` dynamically):
  ```python
  _SYSTEM = (
      "Trade Island. You consume 1 grain/round. {grain_rounds_left} rounds of grain left. "
      "At 0 grain: -1VP/round permanently. "
      "Buildings: Market(wood=2+stone=2→3VP), Granary(grain=3+wood=1→3VP+2grain/rnd), Tower(stone=2+clay=2→3VP). "
      "Accept trades that move you toward a building or give you grain. "
      "Counter-propose instead of flat declining if the offer is close. "
      'JSON: {"accepted":true|false,"counter":{"wood":0,"stone":0,"grain":0,"clay":0,"fiber":0}|null}'
  )
  ```
- User message: add proposer's grain and VP context: `"{proposer_id} (vp={proposer_vp}, grain={proposer_grain}) offers: {give} for your {want}."`
- Inject `grain_rounds_left = agent.inventory.get('grain', 0)` from caller.

**Step 8: Rewrite act prompt with grain urgency and others' inventory (CF5, SF2)**
- File: `src/prompts/agent_action.py`
- New user message format:
  ```
  R{round}/25. Agent:{agent_id}. Grain:{grain} ({grain_rounds_left}rnd left, -1VP/rnd if 0). VP:{vp}.
  Inv: wood={w} stone={s} grain={g} clay={c} fiber={f}.
  Others: {space-sep list: agentN(vp=X,grain=Y) for all other agents}
  Need for Market:wood=2+stone=2 Tower:stone=2+clay=2 Granary:grain=3+wood=1
  {mem_line}
  Act?
  ```
- Compute `grain_rounds_left = agent.inventory.get('grain', 0)` (grain lasts exactly that many rounds at 1/round).

**Step 9: Rewrite reflection prompt (CF6)**
- File: `src/prompts/reflection.py`
- New system message:
  ```python
  _SYSTEM = (
      "You play Trade Island. Resources: wood, stone, grain, clay, fiber — these 5 only, nothing else. "
      "Buildings: Market(wood=2+stone=2→3VP), Granary(grain=3+wood=1→3VP+2grain/rnd), Tower(stone=2+clay=2→3VP). "
      "These 3 buildings only — no others exist. "
      "Grain: you consume 1/round. Starvation (grain=0) = -1VP/round. "
      "Reflect in 3 sentences: "
      "(1) survival status and grain plan (how many rounds of grain left, how to get more), "
      "(2) which building to target next round and why, "
      "(3) which specific agent to trade with and what to offer."
  )
  ```
- This eliminates hallucination of "glass production", "gold mines", etc.

**Step 10: Compress reflection memory to structured 50-char summaries (SF1)**
- File: `src/simulation/agent.py` (or wherever memory is stored)
- At write time, compress reflection prose to structured summary:
  ```python
  def _compress_reflection(raw: str, grain: int, round_num: int) -> str:
      # Simple compression: truncate to 80 chars, prefix with round/grain context
      summary = f"r{round_num}:g={grain} {raw[:60].replace(chr(10), ' ')}"
      return summary[:80]
  ```
- Store compressed form in `agent.memory` list. Keep last 3 entries only. Store full reflection separately in the JSONL log.
- This fixes the token budget issue: 3 × 80 chars ≈ 60 tokens (vs 3 × 200 chars ≈ 150 tokens).

---

### Phase 3 — Engineering (CF7–CF8, SF3, SF10)

**Step 11: Add resource key normalization function (CF7)**
- File: `src/simulation/game.py`
- Add at top of file:
  ```python
  _KEY_MAP = {
      "W": "wood", "S": "stone", "G": "grain", "C": "clay", "F": "fiber",
      "w": "wood", "s": "stone", "g": "grain", "c": "clay", "f": "fiber",
  }
  def _normalize_resources(d: dict | None) -> dict:
      if not d:
          return {}
      return {_KEY_MAP.get(k, k): v for k, v in d.items()}
  ```
- Apply `_normalize_resources` to `give`, `want`, and `counter` dicts immediately after parsing agent action.

**Step 12: Fix counter-offer double-deduction bug (CF8)**
- File: `src/simulation/game.py`
- In the trade resolution block, when a counter-offer exists, it **replaces** `want` entirely:
  ```python
  # If responder provided a counter, it replaces the proposer's want entirely.
  # Proposer gives: give (deduct from proposer, add to responder)
  # Responder gives: counter (deduct from responder, add to proposer)
  if counter:
      effective_receive = _normalize_resources(counter)
  else:
      effective_receive = _normalize_resources(want)
  
  # Apply proposer's give
  for res, qty in _normalize_resources(give).items():
      proposer.inventory[res] = max(0, proposer.inventory.get(res, 0) - qty)
      responder.inventory[res] = responder.inventory.get(res, 0) + qty
  
  # Apply responder's give (effective_receive)
  for res, qty in effective_receive.items():
      responder.inventory[res] = max(0, responder.inventory.get(res, 0) - qty)
      proposer.inventory[res] = proposer.inventory.get(res, 0) + qty
  ```
- Remove the old code that applied both `counter` AND `want` simultaneously.

**Step 13: Fix pairing label for phase0 config (SF3)**
- File: `src/simulation/game.py` (or wherever `is_mono` is computed)
- Change:
  ```python
  # BEFORE (buggy):
  is_mono = config_name.endswith("-mono") or (not config_name.startswith("pairwise-"))
  # AFTER (correct):
  is_mono = config_name.endswith("-mono")
  ```
- This one-line fix ensures phase0 cross-family trades get correct pairings (`llama_deepseek` not `llama_mono`).

**Step 14: Fix rate limit sleep (SF10)**
- File: `src/simulation/llm_router.py`
- Change `time.sleep(0.1)` to `time.sleep(0.5)`.
- This matches the S04-RESEARCH.md spec and prevents Gemini 429 bursts.

---

### Phase 4 — Observability (SF4–SF6, NH4)

**Step 15: Add `raw_action` to agent_action events (SF4)**
- File: `src/simulation/game.py`
- In the `agent_action` log call, add `raw_action=action` (the full parsed dict before normalization).
- Also add `normalized_action=normalized_action` (after normalization, to distinguish).

**Step 16: Add `build_failed` event with reason (SF5)**
- File: `src/simulation/game.py`
- Replace silent `continue` statements in the build resolution block:
  ```python
  if not building_name or building_name not in config.buildings:
      logger.log("build_failed", round=round_num, agent_id=agent.agent_id,
                 model_family=agent.model_family,
                 building=building_name, reason="unknown_building",
                 inventory=dict(agent.inventory))
      continue
  if not affordable:
      logger.log("build_failed", round=round_num, agent_id=agent.agent_id,
                 model_family=agent.model_family,
                 building=building_name, reason="insufficient_resources",
                 inventory=dict(agent.inventory),
                 cost=dict(config.buildings[building_name]["cost"]))
      continue
  ```

**Step 17: Add `inventory` dict to round_end events (SF6)**
- File: `src/simulation/game.py`
- In the `round_end` log call, add `inventory=dict(agent.inventory)`.
- This allows trajectory analysis (resource Gini over time, grain depletion curves) without event reconstruction.

**Step 18: Log actual model version from API response (NH4)**
- File: `src/simulation/llm_router.py`
- After `response = litellm.completion(...)`, capture `response.model` if available:
  ```python
  actual_model = getattr(response, 'model', None) or model_string
  ```
- Return `actual_model` alongside the completion text and cost.
- In `game.py`, log `model_version_used` in `game_start` events per agent.

---

### Phase 5 — Tests (SF7, NH7)

**Step 19: Fix token budget test assertion (SF7)**
- File: `tests/test_smoke.py`
- Find the `test_act_within_budget` test.
- Change assertion from `assert tok <= 108` to `assert tok <= 160`.
- Add a comment: `# Budget increased after S03: Granary effect description added; urgency injection adds ~30 tok.`

**Step 20: Create `tests/test_mechanics.py` (NH7)**
- New file: `tests/test_mechanics.py`
- Write the following 9 unit tests (mock LLM, no real API calls):

  1. `test_build_affects_inventory` — build Market, verify w−2 s−2 deducted, vp+3
  2. `test_grain_consumption_depletes` — after N rounds, grain = start − N + (N × grain_income)
  3. `test_hunger_penalty_applied` — when grain=0 at consumption, vp−1 that round
  4. `test_granary_income` — build Granary at round 1, verify +2 grain added each subsequent round
  5. `test_resource_specialization` — with specialization=True, agents have different starting inventories
  6. `test_pairing_label_phase0` — phase0 config cross-family trade gets `llama_deepseek` not `llama_mono`
  7. `test_action_key_normalization` — `_normalize_resources({"G": 2, "W": 1})` returns `{"grain": 2, "wood": 1}`
  8. `test_build_failed_event_logged` — insufficient-resource build attempt emits `build_failed` event
  9. `test_early_win_condition` — agent reaching 12VP triggers game end before round 25
  10. `test_hoard_gives_specialty_resource` — hoard action gives +1 of agent's specialty resource

---

### Phase 6 — Reproducibility + Documentation (NH1–NH3, NH5–NH6)

**Step 21: Generate requirements-lock.txt (NH1)**
```bash
pip freeze > requirements-lock.txt
```
Commit this file.

**Step 22: Create .env.example (NH2)**
- File: `.env.example`
- Content:
  ```
  # Trade Island Simulation — API Key Template
  # Copy to .env and fill in your keys. Never commit .env.
  GROQ_API_KEY=your_groq_api_key_here
  OPENROUTER_API_KEY=your_openrouter_api_key_here
  GEMINI_API_KEY=your_google_ai_studio_key_here
  MISTRAL_API_KEY=your_mistral_api_key_here
  ```

**Step 23: Wire seed to actual RNG (NH3)**
- File: `src/simulation/game.py`
- At game start, after generating `game_id` and computing seed:
  ```python
  seed = int(game_id, 16) % (2**32)
  import random
  rng = random.Random(seed)
  ```
- Use `rng` for all randomness in the game (specialty archetype rotation, agent order shuffles, etc.).
- Log `seed` in `game_start` event (already done — just wire it to actual RNG use).

**Step 24: Document DeepSeek R1 reflection behavioral split (NH5)**
- File: `docs/limitations.md` (create if not exists)
- Add: "DeepSeek agents use R1 (reasoning mode) for reflections but V3 (chat mode) for actions. This creates a within-family behavioral split: action decisions are chat-model decisions, but memory (which influences actions) is reasoning-model output. This is intentional per D024 but introduces an undocumented confound for H4."

**Step 25: Update related work in blueprint (NH6)**
- File: `research_blueprint_v6.md` or `docs/related_work.md`
- Add citations:
  - FAIRGAME framework (Buscemi et al., 2025) — 2-player repeated games with same model families
  - "More at Stake" (Buscemi et al., 2026) — extended FAIRGAME analysis
  - "Understanding LLM Agent Behaviours via Game Theory" (Huynh et al., 2025)
- Note paper differentiation: our contribution is a 6-player multi-issue multi-round resource trading game vs their 2-player matrix games. Economic resource trading + VP victory condition creates richer strategic space.

---

## Must-Haves

- [ ] CF1–CF8: all 8 critical failures resolved
- [ ] SF1–SF10: all 10 should-fix issues resolved
- [ ] NH1–NH4, NH7: reproducibility + science + test issues resolved
- [ ] `pytest tests/ -v` passes with 0 failures (includes 10 new mechanics tests)
- [ ] No import errors or runtime crashes on `python scripts/run_game.py --config mistral-mono --games 1`

## Verification

```bash
# All tests pass
pytest tests/ -v
# → X passed, 0 failed

# No stale assertions
pytest tests/test_smoke.py::test_act_within_budget -v
# → PASSED

# Normalization works
python3 -c "
from src.simulation.game import _normalize_resources
print(_normalize_resources({'G':2,'W':1,'S':3}))
# → {'grain': 2, 'wood': 1, 'stone': 3}
"

# Pairing label fix
python3 -c "
is_mono = 'phase0'.endswith('-mono')
print('is_mono:', is_mono)
# → is_mono: False
"

# Sleep is 0.5s
grep 'time.sleep' src/simulation/llm_router.py
# → time.sleep(0.5)

# Lock file exists
test -f requirements-lock.txt && echo ok

# .env.example exists
test -f .env.example && echo ok
```

## Inputs

- T01 complete: cost tracking, crash-resume, dynamic GM ✅
- T02 complete: format decisions locked (D041–D044) ✅
- MASTER_AUDIT_2026-03-15.md: full issue list with exact code-level fixes
- SIMULATION_AUDIT.md: detailed diagnosis per layer

## Expected Output

- Modified: `src/simulation/game.py`, `src/simulation/config.py`, `src/simulation/agent.py`, `src/simulation/llm_router.py`
- Modified: `src/prompts/agent_action.py`, `src/prompts/trade_response.py`, `src/prompts/reflection.py`
- Modified: `tests/test_smoke.py` (SF7 assertion update)
- New: `tests/test_mechanics.py` (10 unit tests)
- New: `requirements-lock.txt`
- New: `.env.example`
- New: `docs/limitations.md`
- Updated: `research_blueprint_v6.md` (related work)
- Updated: `.gsd/DECISIONS.md` (D046–D050 for repair decisions)
