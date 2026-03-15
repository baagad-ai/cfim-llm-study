# M001: Infrastructure + Phase 0 — Context

**Gathered:** 2026-03-15
**Status:** Ready for planning (S02 next)

---

## Project Description

A controlled behavioral experiment comparing four LLM families (Llama 3.3 70B, DeepSeek V3.2, Gemini 2.5 Flash, Mistral Small 3.1) via 335 games of "Trade Island" — a 6-agent, 25-round economic negotiation game. The simulation measures cooperation, strategic depth, and adaptation across monoculture and pairwise configurations. Target venues: NeurIPS 2026 workshop + AAMAS 2027 full paper.

## Why This Milestone

M001 builds the entire simulation stack from scratch and validates it with 30 calibration games before any production data is collected. OSF pre-registration must be locked before Phase 1 begins (scientific integrity requirement, D011).

## User-Visible Outcome

### When this milestone is complete, the user can:
- Run `python scripts/run_game.py --config mistral-mono --games 1` and get a complete 25-round game with JSONL logs
- Run `python scripts/run_game.py --config phase0 --games 30` and get all 30 calibration games under $1.50
- Verify all 4 providers work end-to-end in simulation (not just connectivity ping)
- Point to an OSF pre-registration URL locked before any Phase 1 data exists

### Entry point / environment
- Entry point: `python scripts/run_game.py --config <name> --games <n>`
- Environment: local dev, `.venv/` Python 3.14, real paid APIs
- Live dependencies: Groq (Llama), OpenRouter (DeepSeek), Google AI Studio Paid (Gemini), Mistral La Plateforme

## Completion Class

- Contract complete means: single smoke-test game runs 25 rounds, JSONL valid, cost ≤$0.02
- Integration complete means: all 4 model families participate in a single pairwise game, per-agent routing verified
- Operational complete means: 30 Phase 0 games complete under $1.50; crash-resume tested; OSF pre-registered

## Final Integrated Acceptance

To call M001 complete, we must prove:
- `python scripts/run_game.py --config mistral-mono --games 1` → 25 rounds, valid JSONL, ≤$0.02
- `python scripts/run_game.py --config phase0 --games 30` → 30 games complete, $0.00–$1.50
- OSF pre-registration confirmation URL recorded in `data/metadata/osf_registration.json`
- `requirements-lock.txt` committed with all exact pinned versions

## Risks and Unknowns

- **Concordia version drift** — Installed as `gdm-concordia==2.4.0`, not 2.0.0 as blueprint assumed. Concordia's `LanguageModel` interface is `sample_text(prompt)` — not chat completions. Decision: use custom loop (see §Implementation Decisions below).
- **DeepSeek R1 via OpenRouter pricing** — R1 is ~5× more expensive than V3 ($2.19 vs $0.38 output). User has accepted this for reflection calls. Must monitor Phase 0 cost carefully.
- **Gemini 429 bursts** — Paid tier confirmed active; transient 429s seen during burst tests. LiteLLM retry (3×, 2s) handles this. Monitor during multi-model games.
- **Phase 0 JSON parse rate** — If <90% on any model, switch that model to verbose format (D012). May require a Phase 0 re-run.

## Existing Codebase / Prior Art

- `scripts/test_connectivity.py` — 4-provider ping test, all pass. Per-provider call signatures confirmed and documented.
- `src/analysis/h1-h4_*.py` — Pre-registration analysis stubs, committed before any data collected.
- `config/litellm_config.yaml` — All 4 providers configured.
- `.env` / `.env.example` — API keys in place.
- `src/simulation/__init__.py` — Empty, ready for S02 implementation.

## Relevant Requirements

- R002 — Simulation engine: Concordia v2.0 (now 2.4.0) + Trade Island game loop
- R011 — Per-agent LLM routing for monoculture and pairwise configurations
- D001–D022 — All prior architecture decisions (see `.gsd/DECISIONS.md`)

## Scope

### In Scope

- Full Trade Island simulation engine (custom loop — see implementation decisions)
- Per-agent LLM routing (LiteLLMLanguageModel wrapper over litellm.completion)
- JSONL event logging + JSON checkpoint/resume
- All 6 prompt templates (cache-optimized, prefix-first per blueprint §2.2–2.5)
- Phase 0: 30 calibration games (format ablation + GM sensitivity)
- OSF pre-registration (before Phase 1)
- requirements-lock.txt committed

### Out of Scope / Non-Goals

- Phase 1/2/3 production runs (M002–M004)
- Analysis pipeline execution (stubs committed, not run)
- GitHub remote push (deferred to S05/T03)
- Concordia entity/component system integration (decision D023: custom loop chosen)

## Technical Constraints

- Python 3.14, `.venv/` local venv
- `litellm.drop_params = True` globally — always set before any API call
- `gdm-concordia==2.4.0` installed from GitHub (not PyPI — `concordia-ai` does not exist on PyPI)
- All per-provider workarounds from D018–D022 apply to every API call in S02+

## Integration Points

- Groq API — Llama 3.3 70B agent calls, JSON mode enabled
- OpenRouter API — DeepSeek V3.2 agent calls + R1 reflection calls
- Google AI Studio (Paid) — Gemini 2.5 Flash agent + reflection calls (thinking disabled, max_tokens=200)
- Mistral La Plateforme — Mistral agent calls + GM resolution calls, `mistral-small-2506`

---

## Implementation Decisions

These decisions came out of the discuss phase (gathered 2026-03-15). They supersede or clarify blueprint assumptions where noted.

### D023: Concordia integration depth → Custom loop (NOT Concordia entity system)

**Decision:** Build a custom 200-line game loop that calls `litellm.completion()` directly. Do NOT use Concordia's entity/component/simultaneous-engine architecture.

**Rationale:**
- Concordia's `LanguageModel` interface requires `sample_text(prompt: str)` — a text-completion interface, not chat completions. Bridging our per-provider chat call signatures (with `thinking={}`, `response_format={}`, etc.) via that interface adds an indirection layer over a working system.
- The per-provider workarounds (D018–D022) are tightly coupled to litellm's chat completion kwargs — they cannot pass cleanly through `sample_text()`.
- A custom loop gives full control over the JSONL event schema, checkpoint format, phase ordering, and cost tracking — without framework constraints.
- Concordia's **Inventory component** may still be used as a reference implementation or imported directly if convenient, but is not required.
- Concordia's marketplace prefab is a clearing-house (bids/asks) — not bilateral proposals. Not usable for Trade Island.

**Files this affects:** All of `src/simulation/` — use plain Python, not Concordia entity classes.

**Recorded in DECISIONS.md as D023.**

---

### D024: DeepSeek reflection model → R1 via OpenRouter

**Decision:** Use `openrouter/deepseek/deepseek-r1` for DeepSeek agent reflection calls (every 5 rounds). Use `openrouter/deepseek/deepseek-chat` (V3.2) for all action/response/GM calls.

**Rationale:** User accepted the cost premium (~$0.45 extra across Phase 0 30 games) for richer reflection content. D007 stated "DeepSeek agents may use reasoner mode for reflection" — this confirms it. Blueprint §2.5 intent preserved.

**Cost impact:** ~$0.015 extra per DeepSeek-monoculture game from R1 reflections. Monitor in Phase 0.

**Warning:** D007's "no extra per-token cost" claim was incorrect — OpenRouter prices R1 at $0.55/$2.19 vs V3.2 at $0.26/$0.38. R1 output is ~5.8× more expensive. The reasoner chain can be long. Cap reflection `max_tokens=800` to prevent runaway costs. Document this in DECISIONS.md as D024.

**Recorded in DECISIONS.md as D024.**

---

### D025: Checkpoint strategy → JSON per-round files

**Decision:** After each round, write `data/raw/{game_id}/checkpoint_r{N:02d}.json` with full serialized game state. On resume, load the highest-numbered checkpoint and continue from round N+1.

**Rationale:** Simple, deterministic, no additional dependencies. Sufficient for single-threaded sequential games. State includes: round number, all agent inventories, VP counters, reflection histories, pending trade state, random seed.

**Recorded in DECISIONS.md as D025.**

---

## Agent's Discretion

The following areas were not explicitly asked about — agent decides during S02 planning/execution:

- Whether to import `concordia.components.game_master.inventory.Inventory` as a reference for resource bounds checking, or implement inventory tracking as a simple dict. (Recommendation: simple dict — the Inventory component uses LLM chain-of-thought to infer changes, which is exactly what we want to avoid in favor of deterministic JSON parsing.)
- Exact file layout within `src/simulation/` (agent.py, gm.py, game.py, config.py, llm_router.py, logger.py as specified in S02)
- Whether to use `tenacity` (already in requirements.txt) for retry logic on top of litellm's built-in retry, or rely solely on litellm's `num_retries=3`
- Internal test structure: `pytest` is in requirements.txt; write at minimum a `tests/test_smoke.py` that verifies a 3-round mock game with stubbed LLM responses

## Deferred Ideas

- Concordia entity architecture may be revisited for M002+ if we need richer agent memory (associative memory bank). Not needed for M001.
- Async parallel agent calls within a round: blueprint mentioned "simultaneous" — implement as sequential for Phase 0 to keep debugging simple. Parallelize in M002 if Phase 0 is stable.
- DeepSeek R1 for agent action decisions (not just reflection): out of scope per D004 — "study is about families"; reasoner mode for actions would change behavioral signatures vs V3.2 chat mode.

## Open Questions

- **gdm-concordia 2.4.0 vs 2.0.0:** The installed version is ahead of the blueprint's target. The API appears stable. No known breaking changes relevant to us since we're not using the entity system. Log the version discrepancy in DECISIONS.md.
- **sentence-transformers install:** Required by analysis stack but not yet installed. May have heavy torch dependency — check install time and size before Phase 0 run.
