# S01: RNE Engine + LLM Router

**Goal:** Build the Repeated Negotiated Exchange (RNE) 2-agent game engine and wire it to LiteLLM so a real 35-round bilateral game runs end-to-end with mock LLM responses in tests and real Mistral+Llama in the smoke run.
**Demo:** `python scripts/run_rne.py --family-a mistral --family-b llama --condition A --disclosure blind --games 1` completes 35 rounds, writes valid JSONL to `data/study1/{session_id}/game.jsonl` and `summary.json` with M1–M4 computed. `pytest tests/test_rne.py` passes all mock-mode tests.

## Must-Haves

- `src/simulation/config.py` — `RNEConfig` Pydantic model + `GameConfig.from_rne()` factory
- `src/simulation/logger.py` — `GameLogger` line-buffered JSONL writer
- `src/simulation/llm_router.py` — `call_llm(family, messages, mock_response)` + 7-family `PROVIDER_KWARGS` + `strip_md`
- `tests/test_rne.py` — full test coverage for T01 components; T02+ as skipped stubs

## Proof Level

- Integration — RNE engine calls LiteLLM for real Mistral+Llama completions in smoke run
- Mock-mode: `pytest tests/test_rne.py` must pass with no API calls

## Verification

```bash
pytest tests/test_rne.py -v                          # all mock-mode tests pass
python scripts/run_rne.py --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1
# → session dir created, game.jsonl has 35 round_end events
# → summary.json has M1 cooperation_rate between 0.0 and 1.0
# → metadata.json has correct config fields
grep '"event": "perturbation"' data/study1/*/game.jsonl   # fires exactly once at round 20
grep '"event": "game_end"' data/study1/*/game.jsonl | python3 -c \
  "import sys,json; d=json.loads(sys.stdin.read()); assert d['total_cost_usd'] <= 0.05"
```

## Tasks

- [x] **T01: Config, Logger, and LLM Router** `est:1h`
  > DONE. `RNEConfig` (7-family validated), `GameLogger`, `call_llm` + 7-family `PROVIDER_KWARGS`. Tests pass.

- [x] **T02: RNE Engine** `est:2h`
  > DONE. `RNERunner.run_session()`: 35-round loop, simultaneous proposals, compatibility check, respond call, trade settlement, 10% decay, perturbation at round 20, summary.json, metadata.json. 47 tests pass in `tests/test_rne.py`.

- [x] **T03: Metrics (M1–M4)** `est:1h`
  > DONE. M1–M4 computed in `_compute_metrics()` inside `rne_game.py`. M1=cooperation_rate, M2=exploitation_delta, M3=adaptation_lag, M4=betrayal_recovery. Covered by `test_m1_computation` and engine integration tests.

- [x] **T04: run_rne.py CLI + smoke run** `est:1h`
  > NEXT. Write `scripts/run_rne.py` CLI. Run real Mistral×Llama smoke session (≥1 accepted trade, cost ≤$0.05). Verify 70 round_end events and 1 perturbation event in `data/study1/`.
