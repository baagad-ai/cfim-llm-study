# M001: RNE Engine + Phase 0 Calibration — Roadmap

**Vision:** Complete RNE simulation stack validated with 240 Phase 0 sessions. OSF pre-registered. Ready to begin Study 1 full CFIM data collection (M002).

---

## Success Criteria

- `pytest tests/test_rne.py` passes all mock-mode tests (0 failures)
- `python scripts/run_rne.py --family-a mistral --family-b llama --condition A --disclosure blind --framing neutral --games 1` completes: 35 rounds, 70 `round_end` events, 1 `perturbation` event, `summary.json` with M1 ∈ [0.0, 1.0], `total_cost_usd ≤ 0.05`
- Phase 0: 240 sessions complete; ≥90% JSON parse rate per family; ≥1 completed trade per session; calibration report written
- OSF registration submitted; URL in `data/metadata/osf_registration.json`
- Total cost ≤ $15

---

## Key Risks

- **Zero trade acceptance** — LLMs may never produce compatible proposals. M1=0 kills the study. Smoke test in S01/T02 retires this before anything else is built.
- **Gemini parse instability** — 2.5 Flash occasionally ignores JSON instruction. D047 (json_object re-enabled) mitigates; Phase 0 parse rate measurement confirms.
- **Disclosure effect too small to detect** — If |M6|≈0, H3 is null. Acceptable; null result is publishable. Phase 0 gives early signal.

---

## Proof Strategy

- Trade acceptance → S01/T02 real smoke run: ≥1 `trade_result accepted=true` in a 35-round Mistral×Llama session
- Prompt format reliability → S03: measure parse rate per family across 240 Phase 0 sessions
- Disclosure effect → qualitative signal in Phase 0 report; formal test is M002

---

## Slices

- [x] **S01: RNE Engine + LLM Router** `risk:high` `depends:[]`
  > After this: `run_rne.py` completes a real 35-round game and writes valid JSONL. `pytest tests/test_rne.py` passes all mock-mode tests. 7-family routing verified.
  > **STATUS:** T01/T02/T03 done. T04 (run_rne.py CLI + smoke run) is NEXT.

- [x] **S02: RNE Prompt Architecture** `risk:medium` `depends:[S01]`
  > After this: all 3 conditions × 3 framings × 2 disclosure variants produce correctly structured LLM messages. `parse_rne_response` handles all 4 failure modes. `pytest tests/test_rne_prompts.py` passes.

- [ ] **S03: Phase 0 Calibration** `risk:medium` `depends:[S01,S02]`
  > After this: 240 sessions run; parse rate ≥90% per family; `data/phase0/calibration_report.md` with go/no-go for Study 1.

- [ ] **S04: OSF Pre-Registration** `risk:low` `depends:[S01]`
  > After this: OSF registration formally submitted; URL recorded. Unblocks M002.
  > **STATUS:** T01 done (docs + stubs written). T02 requires human OSF submission.

---

## S01 — RNE Engine + LLM Router (IN PROGRESS)

**Status:** T01/T02/T03 complete. T04 (run_rne.py CLI + smoke run) is NEXT.

### Tasks

- [x] **T01: Config, Logger, and LLM Router** `est:1h`
  > `RNEConfig` (7-family validated), `GameLogger`, `call_llm` + 7-family `PROVIDER_KWARGS`. Tests pass.

- [x] **T02: RNE Game Engine** `est:2h`
  > `src/simulation/rne_game.py` — `RNERunner.run_session()`: 35-round loop, simultaneous proposals, compatibility check, respond call, trade settlement, 10% decay, perturbation at round 20. 47 tests pass.

- [x] **T03: Metrics (M1–M4)** `est:1h`
  > `_compute_metrics()` in `rne_game.py`. M1=cooperation_rate, M2=exploitation_delta, M3=adaptation_lag, M4=betrayal_recovery. Covered by engine integration tests.

- [ ] **T04: run_rne.py CLI + smoke run** `est:1h`
  > **NEXT.** `scripts/run_rne.py` CLI. Real Mistral×Llama smoke session. Verify 70 round_end events, 1 perturbation, ≥1 accepted trade, cost ≤$0.05.

### S01 Verification

```bash
pytest tests/test_rne.py -v                          # all mock-mode tests pass

python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1

grep '"event": "round_end"' data/study1/*/game.jsonl | wc -l  # → 70
grep '"event": "perturbation"' data/study1/*/game.jsonl | wc -l  # → 1

python -c "
import json, pathlib
s = json.loads(next(pathlib.Path('data/study1').glob('*/summary.json')).read_text())
assert 0.0 <= s['cooperation_rate'] <= 1.0
assert s['total_cost_usd'] <= 0.05
print('smoke ok, cost:', s['total_cost_usd'])
"
```

---

## S02 — RNE Prompt Architecture

**Status:** Not started. Starts after S01/T04 complete.

### Must-Haves

- `src/prompts/rne_prompts.py` with `build_system_prompt(condition, framing)` (9 variants), `build_round_messages(...)` with disclosure injection, `parse_rne_response(raw)`
- `tests/test_rne_prompts.py` covering all 4 parser failure modes + disclosure injection + framing token counts

### Tasks

- [ ] **T01: System prompt variants — 3 conditions × 3 framings** `est:1h`
- [ ] **T02: Round messages + disclosure injection** `est:1h`
- [ ] **T03: Tolerant parser + full test suite + smoke run** `est:45m`

---

## S03 — Phase 0 Calibration

**Status:** Not started. Starts after S01 + S02 complete.

### Must-Haves

- `scripts/run_phase0.py` — runs 4 families × 10 sessions × 3 conditions × 2 disclosure = 240 sessions
- JSON parse rate ≥90% per family; ≥1 completed trade per session; cost ≤$12
- `data/phase0/calibration_report.md` with Go/No-Go recommendation

### Tasks

- [ ] **T01: run_phase0.py + 4-family test run** `est:1h`
- [ ] **T02: Full 240-session run** `est:30m (wall time)`
- [ ] **T03: Calibration report** `est:45m`

---

## S04 — OSF Pre-Registration

**Status:** T01 done. T02 requires human OSF submission. Can proceed in parallel with S03.

### Must-Haves

- `docs/osf_preregistration.md` ✅ written
- `src/analysis/h1–h5_*.py` stubs ✅ committed
- `data/metadata/osf_registration.json` with real registration URL (pending T02)

### Tasks

- [x] **T01: Write pre-registration document and analysis stubs** `est:2h`
- [ ] **T02: Create OSF project and submit formal registration** `est:1h` *(human action)*
- [ ] **T03: Record URL + commit** `est:10m`

---

## Planning Notes

**Why T02 (engine) before T03 (CLI):** Engine correctness is the primary risk. The CLI is just argparse wiring. Build and test the engine loop first; wire the CLI only after the inline smoke test passes.

**S02 can reuse json_utils.py:** `parse_agent_response` from `src/prompts/json_utils.py` handles the tolerant parsing already. `rne_prompts.py` should call it rather than re-implementing.

**S04 parallelism:** OSF registration requires only committed analysis stubs (done) and the `docs/osf_preregistration.md` (done). It can be submitted any time after S01 completes — it does not need Phase 0 data. The hard constraint is submission before M002 starts.
