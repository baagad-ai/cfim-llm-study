# T01: run_phase0.py + 4-family test run

**Estimate:** 1h

## Goal

Write `scripts/run_phase0.py` CLI. Run a 4-session smoke (1 per family) to confirm all providers route correctly. Verify ≥1 accepted trade per smoke session.

## Must-Haves

- `scripts/run_phase0.py` exists and is importable
- `--smoke` mode runs exactly 4 sessions (1 per family, condition A, blind)
- `--mock` mode runs with zero API cost (no real calls)
- All 4 providers (llama/groq, deepseek/openrouter, gemini, mistral) route without error
- Session output lands in `data/phase0/sessions/` with `summary.json` + `game.jsonl` + `metadata.json`
- ≥1 trade accepted across the 4 smoke sessions
- 0 parse failures across all 4 smoke sessions

## Files

- `scripts/run_phase0.py` — new
