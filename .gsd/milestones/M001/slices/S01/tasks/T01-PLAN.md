---
estimated_steps: 6
estimated_files: 4
---

# T01: Config, Logger, and LLM Router

**Slice:** S01 — RNE Engine + LLM Router
**Milestone:** M001

## Description

Lock the JSONL schema and routing surface that everything else in M001 depends on. `RNEConfig` is the single configuration object for Study 1. `GameLogger` writes line-buffered JSONL. `call_llm` is the single routing entry point with correct per-provider kwargs and float cost guard.

## Steps

1. Create `src/simulation/__init__.py` (export `RNEConfig`)
2. Write `src/simulation/config.py` — `RNEConfig` Pydantic BaseModel with all fields; `GameConfig.from_rne()` factory
3. Write `src/simulation/logger.py` — `GameLogger` with line-buffered JSONL; `log_round_end` emitting flat fields
4. Write `src/simulation/llm_router.py` — `call_llm`, `PROVIDER_KWARGS`, `strip_md`; `litellm.drop_params = True` at module level; float cost guard
5. Verify imports and spot-check config validation
6. Verify logger writes readable JSONL to a temp path

## Must-Haves

- [x] `RNEConfig` has fields: `family_a`, `family_b`, `condition` (A/B/C), `disclosure` (blind/disclosed), `prompt_framing` (neutral/social/strategic), `rounds=35`, `decay_rate=0.10`, `perturbation_round=20`, `session_id` (auto-generated uuid hex[:8])
- [x] `GameLogger.log(event, **fields)` writes one JSON line to `data/study1/{session_id}/game.jsonl` with `ts` (ISO8601) prepended; file is line-buffered (`buffering=1`)
- [x] `call_llm(family, messages, mock_response=None)` returns litellm response; uses correct per-provider kwargs from `PROVIDER_KWARGS`; cost guard `(r._hidden_params.get("response_cost") or 0.0)` (not `or 0`)
- [x] `litellm.drop_params = True` set at module level in `llm_router.py`
- [x] All 7 provider entries in `PROVIDER_KWARGS`: llama (Groq, json_object, max_tokens=150), deepseek (OpenRouter, json_object, max_tokens=150), gemini (Google, thinking disabled, max_tokens=200, NO response_format per D021), mistral (Mistral, json_object, max_tokens=150), gpt4o-mini (OpenAI, json_object, max_tokens=150), qwen (Together.ai, json_object, max_tokens=150), phi4 (Together.ai, json_object, max_tokens=150)

## Verification

- `python -c "from src.simulation.config import RNEConfig; c = RNEConfig(family_a='mistral', family_b='llama', condition='A'); assert c.rounds == 35; assert c.decay_rate == 0.10; assert len(c.session_id) == 8; print('config ok')"`
- `python -c "from src.simulation.logger import GameLogger; import tempfile, pathlib, json; t = tempfile.mkdtemp(); l = GameLogger('test123', pathlib.Path(t)); l.log('round_end', round=1, agent='a0', resources={'wood':3}); line = (pathlib.Path(t)/'game.jsonl').read_text().strip(); d = json.loads(line); assert d['event']=='round_end'; assert d['round']==1; print('logger ok')"`
- `python -c "from src.simulation.llm_router import call_llm, PROVIDER_KWARGS; assert 'gemini' in PROVIDER_KWARGS; assert 'response_format' not in PROVIDER_KWARGS['gemini']; assert 'thinking' in PROVIDER_KWARGS['gemini']; print('router ok')"`
