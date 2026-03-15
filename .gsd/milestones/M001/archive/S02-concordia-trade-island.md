# S02: Concordia v2.0 Integration + Trade Island

**Milestone:** M001
**Status:** ⬜ next
**Estimated time:** 1-2 weeks (varies on marketplace evaluation result)
**Requirements:** R002, R011
**Depends on:** S01 ✅

## Goal

Concordia v2.0 running Trade Island simulations end-to-end. Per-round JSONL logs. Crash-safe checkpoint saves. GM trade resolution working. Single smoke-test game completes at ≤$0.02.

## Context from S01

The LiteLLM layer is confirmed working with these per-provider call signatures:

```python
import litellm
litellm.drop_params = True  # MUST be set globally

# Groq / Llama
litellm.completion(model='groq/llama-3.3-70b-versatile', api_key=GROQ_API_KEY,
    messages=[...], max_tokens=150, response_format={'type':'json_object'})

# DeepSeek via OpenRouter
litellm.completion(model='openrouter/deepseek/deepseek-chat', api_key=OPENROUTER_API_KEY,
    messages=[...], max_tokens=150, response_format={'type':'json_object'})

# Gemini 2.5 Flash — NO json_object, thinking MUST be disabled
litellm.completion(model='gemini/gemini-2.5-flash', api_key=GOOGLE_API_KEY,
    messages=[...], max_tokens=200,
    thinking={'type': 'disabled', 'budget_tokens': 0})
# Strip markdown fences from response before json.loads()

# Mistral
litellm.completion(model='mistral/mistral-small-2506', api_key=MISTRAL_API_KEY,
    messages=[...], max_tokens=150, response_format={'type':'json_object'})
```

## Tasks

### T01: Install full dependency stack
- Activate `.venv/` and install remaining deps from `requirements.txt`:
  `concordia-ai`, `polars`, `statsmodels`, `scikit-learn`, `networkx`,
  `sentence-transformers`, `seaborn`, `matplotlib`, `pydantic`, `pytest`, `jupyter`
- Verify: `python -c "import concordia; print(concordia.__version__)"`
- Pin exact versions: `pip freeze > requirements-lock.txt`
- Commit `requirements-lock.txt`

### T02: Concordia v2.0 marketplace evaluation
- Read Concordia v2.0 source / docs for built-in economy/marketplace components
- Answer these questions:
  1. Does it have resource inventory per agent? (W, S, G, Wo, O, C)
  2. Does it support bilateral trade proposals (agent A offers X to B for Y)?
  3. Does it have a GM/arbiter layer for sequential trade resolution?
  4. Does it support per-round VP tracking?
  5. Does `per_agent_llm_override` work as described (native v2.0 feature)?
- **Decision gate:** If ≥3 of 5 fit → extend built-in. Else → build custom.
- Document decision in DECISIONS.md as D023.

### T03: Trade Island component implementation
Based on T02 decision — either extend built-in or build from scratch:

**Agent entity (`src/simulation/agent.py`)**
- Resource inventory: `{"W":0,"S":0,"G":0,"Wo":0,"O":0,"C":0}` — confirmed abbreviations from blueprint §2.2
- VP counter, specialty assignment (one resource type produced each round)
- Reflection memory (last reflection summary, updated every 5 rounds)
- Per-agent LLM binding (model family + api key)

**GM entity (`src/simulation/gm.py`)**
- Input: list of accepted trade pairs + full inventory matrix
- Sequential resolution: process trade 1 → update inventories → process trade 2 → ...
- Double-spending prevention: re-check balances before each trade in sequence
- Output: `{"valid":[bool,...],"reason":["ok"|"<description>",...]}`
- Model: `mistral/mistral-small-2506` (cheapest capable model)

**Game orchestrator (`src/simulation/game.py`)**
- 25-round loop
- Per-round phases (in order):
  1. **Planning phase** (simultaneous): all 6 agents submit action JSON
  2. **Trade negotiation** (simultaneous): agents respond to received proposals
  3. **GM resolution** (sequential): validate accepted trades, update inventories
  4. **Building phase** (sequential): agents attempt builds if resources sufficient
  5. **Grain consumption**: deduct 1G per agent, apply damage if G=0
  6. **Reflection** (every 5 rounds): each agent reflects using own model family
  7. **Checkpoint save**: write round state to disk
- Victory check: first to 12VP wins; else highest VP at round 25

**Config (`src/simulation/config.py`)**
- `GameConfig`: n_agents=6, n_rounds=25, vp_target=12, grain_per_round=1
- `BuildingRecipe`: House(W2+S2→3VP), Provisions(G2+Wo2→3VP), Tools(O2+C2→3VP)
- `ResourceSpecialties`: randomized assignment, recorded as metadata

### T04: Per-agent LLM override wiring (`src/simulation/llm_router.py`)
- `ModelRouter` class: maps agent_id → (model_string, api_key, call_kwargs)
- Monoculture: all 6 agents → same model config
- Pairwise: agents 1-3 → model_A config, agents 4-6 → model_B config
- Gemini agents automatically get `thinking` kwarg injected — never omit it
- DeepSeek reflection agents automatically get `deepseek-r1` model
- Cost tracking: accumulate per-model token counts + cost across game

### T05: Checkpoint + JSONL logging (`src/simulation/logger.py`)
- Per-game log dir: `data/raw/{game_id}/`
- `game.jsonl`: one JSON line per event (schema below)
- `checkpoint_r{N}.json`: full game state after round N (for crash recovery)
- `metadata.json`: game config, model assignments, start time, random seed

**JSONL event schema:**
```json
{"ts":"ISO8601","event":"round_start","round":1}
{"ts":"...","event":"agent_action","round":1,"agent":"a1","model":"llama","action":{"act":"trade","target":"a3","give":"W2","want":"G1"}}
{"ts":"...","event":"trade_proposal","round":1,"from":"a1","to":"a3","give":"W2","want":"G1"}
{"ts":"...","event":"trade_response","round":1,"from":"a3","to":"a1","accepted":true,"counter":null}
{"ts":"...","event":"gm_resolution","round":1,"trade_idx":0,"valid":true,"reason":"ok"}
{"ts":"...","event":"build","round":1,"agent":"a2","building":"house","vp_delta":3}
{"ts":"...","event":"grain_consumption","round":1,"agent":"a1","grain_before":2,"grain_after":1,"damage":false}
{"ts":"...","event":"reflection","round":5,"agent":"a1","model":"llama","summary":"..."}
{"ts":"...","event":"round_end","round":1,"vp_state":{"a1":3,"a2":0,...},"inventories":{...}}
{"ts":"...","event":"game_end","winner":"a3","final_vp":{"a1":3,...},"rounds_played":25}
```

### T06: Single-game smoke test
- Run: `python scripts/run_game.py --config mistral-mono --games 1 --phase 0`
- All-Mistral agents (cheapest, $0.015/game estimated)
- Verify:
  - 25 rounds complete without crash
  - `game.jsonl` has events for all 25 rounds
  - All 5 event types present (action, proposal, response, gm_resolution, round_end)
  - Checkpoint files exist for rounds 5, 10, 15, 20, 25
  - Total cost ≤ $0.02
  - At least 1 trade accepted across the game
  - At least 1 build action across the game
- Manual inspection: does behavior look sensible? Are VPs accumulating?

## Acceptance Criteria

- [ ] `pip install -r requirements.txt` completes, `concordia` importable
- [ ] `requirements-lock.txt` committed with exact pinned versions
- [ ] Concordia v2.0 marketplace evaluation documented (DECISIONS.md D023)
- [ ] Single 25-round game completes end-to-end: `python scripts/run_game.py --config mistral-mono --games 1`
- [ ] `data/raw/{game_id}/game.jsonl` valid, all 25 rounds present
- [ ] Checkpoint crash-resume tested: kill mid-game, resume, correct continuation
- [ ] Per-agent LLM routing verified (Gemini agent calls always include `thinking` kwarg)
- [ ] Cost: one smoke test game ≤ $0.02

## Known Risks for This Slice

- Concordia v2.0 may not be pip-installable yet (could be git-only). If so: `pip install git+https://github.com/google-deepmind/concordia.git@v2.0.0`
- Concordia's Entity-Component API may have changed between v1 and v2.0 — read source, not just docs
- The "simultaneous engine" for agent actions may need explicit async handling — verify Concordia's execution model
- If Concordia is too heavy/complex to adapt: fall back to a lightweight custom loop (document in DECISIONS.md D023)
