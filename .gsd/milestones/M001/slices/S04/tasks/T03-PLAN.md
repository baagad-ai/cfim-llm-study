---
estimated_steps: 6
estimated_files: 2
---

> **RENAMED (2026-03-15 audit):** This task is now T05 in the restructured S04. It was originally T03 but a repair sprint (T03-FIX) and 5-game validation (T04-VALIDATION) were inserted before it. Execution is blocked until T03-FIX + T04-VALIDATION pass. See S04-PLAN.md for updated task sequence.
>
> **Updated prerequisite:** T04-VALIDATION must confirm VP in 3–9 range and trade acceptance >10% before this task begins. Also: GM sensitivity run increased from 5 to **≥10 Llama-GM games** per audit recommendation.

# T05 (was T03): Run 30 Phase 0 calibration games and verify signals

**Slice:** S04 — Phase 0 Calibration (30 games)
**Milestone:** M001

## Description

This is the primary data collection task. Runs all 30 calibration games using the real 4-family `phase0` config, monitors per-game cost against the $1.50 budget, and verifies the key behavioral signals: ≥1 accepted trade (retiring D037), correct 4-provider routing, no duplicate round_end events.

Also runs 5 Llama-GM sensitivity games to quantify the GM confound for the Phase 0 report.

Wall time: ~2–3 hours for the 30-game batch. The sensitivity run adds another ~30 min.

## Steps

1. **Pre-flight check** — before launching 30 games, run a single phase0 game to confirm all 4 providers route:
   ```bash
   python scripts/run_game.py --config phase0 --games 1
   LATEST=$(ls -t data/raw | head -1)
   jq 'select(.event=="game_start") | .model_assignments' data/raw/$LATEST/game.jsonl
   # → should show llama, deepseek, gemini, mistral keys
   jq 'select(.event=="game_end") | .total_cost_usd' data/raw/$LATEST/game.jsonl
   # → should be > 0.0 and < 0.10
   ```
   If the single game succeeds, proceed to the full batch.

2. **Run 30 calibration games**:
   ```bash
   python scripts/run_game.py --config phase0 --games 30
   ```
   This is sequential — no parallelism needed. The 0.5s sleep per call is already in `call_llm()`.

3. **Monitor per-game cost** during or after the run:
   ```bash
   jq 'select(.event=="game_end") | {game_id, total_cost_usd}' data/raw/*/game.jsonl
   ```
   Abort and investigate if any single game exceeds $0.10 (possible R1 cost overrun). If total so far exceeds $1.20 before game 30, pause and reassess.

4. **Verify accepted trades**:
   ```bash
   grep '"accepted": true' data/raw/*/game.jsonl | wc -l
   # Goal: ≥1. If still 0, check: are proposals being generated?
   grep '"action_type": "trade"' data/raw/*/game.jsonl | wc -l
   # If proposals exist but 0 accepted: escalate VP-unlock framing issue (see risk note)
   ```

5. **Run ≥10 Llama-GM sensitivity games** (upgraded from 5 per audit — 5 games is underpowered for confound quantification) — add a `--gm-model` flag to `run_game.py` if not already there from T01, or use a small inline script:
   ```python
   # scripts/run_gm_sensitivity.py
   from src.simulation.config import GameConfig
   from src.simulation.game import GameRunner
   config = GameConfig.from_name('phase0').model_copy(
       update={"gm_model": "groq/llama-3.3-70b-versatile"}
   )
   runner = GameRunner(config)
   for i in range(10):  # minimum 10 per audit recommendation
       print(runner.run_game())
   ```
   Record the 5 game IDs for the Phase 0 report.

6. **Spot-check data integrity** on a sample of games:
   ```bash
   # Pick 3 random game IDs from the batch
   for gid in $(ls data/raw | shuf | head -3); do
     count=$(grep -c '"event": "round_end"' data/raw/$gid/game.jsonl 2>/dev/null || echo 0)
     echo "$gid: $count round_end events (expected 150)"
   done
   # Each should be exactly 150 (25 rounds × 6 agents)
   
   # Check for gm_parse_failure events
   grep gm_parse_failure data/raw/*/game.jsonl | wc -l
   # Small number acceptable; >30 across all 30 games warrants investigation
   ```

## Must-Haves

- [ ] 30 phase0 games complete with `game_end` events in `data/raw/*/game.jsonl`
- [ ] ≥1 `"accepted": true` in any game across all 30
- [ ] All 4 model families present in at least one `game_start.model_assignments`
- [ ] No single game exceeds $0.10; total cost across all 30 games ≤$1.50
- [ ] ≥10 Llama-GM sensitivity games complete (game IDs recorded for T06)
- [ ] No duplicate `round_end` events in any game (spot-checked)

## Verification

```bash
# Game count
ls data/raw | wc -l
# ≥ 31 (30 phase0 + 1 S02 baseline + possibly pre-flight)

# All 30 have game_end (use phase0 config_name to filter)
jq -r 'select(.event=="game_end" and .config_name=="phase0") | .game_id' data/raw/*/game.jsonl | wc -l
# → 30

# Accepted trades
grep '"accepted": true' data/raw/*/game.jsonl | wc -l
# ≥ 1

# Total cost
jq -r 'select(.event=="game_end" and .config_name=="phase0") | .total_cost_usd' \
  data/raw/*/game.jsonl | \
  python3 -c "import sys; vals=[float(l) for l in sys.stdin]; print(f'Total: ${sum(vals):.4f}')"
# → Total: $X.XXXX where X.XXXX ≤ 1.50

# 4-family routing confirmed
jq -r 'select(.event=="game_start" and .config_name=="phase0") | .model_assignments | to_entries[] | .value' \
  data/raw/*/game.jsonl | sort -u
# → deepseek, gemini, llama, mistral
```

## Observability Impact

- Signals added/changed: `game_end.config_name` field distinguishes phase0 games from mistral-mono baseline
- How a future agent inspects this: `jq 'select(.event=="game_end" and .config_name=="phase0")' data/raw/*/game.jsonl` filters to only calibration games
- Failure state exposed: `gm_parse_failure` events with `raw_response` for GM LLM diagnosis; `grep "strategy [234]"` in run logs for per-model parse degradation

## Inputs

- T01 complete: Mistral cost tracking working, GM dynamic provider fixed, `--resume` available
- T02 complete: Format decision locked per model in DECISIONS.md (D041–D044); verbose variant available if needed
- `.env` with all 4 API keys: `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `GEMINI_API_KEY`, `MISTRAL_API_KEY`
- `GameConfig.from_name('phase0')` — confirmed real 4-family mix from S03

## Expected Output

- `data/raw/{30 new game_ids}/game.jsonl` — 30 complete phase0 calibration game logs
- `data/raw/{5 sensitivity game_ids}/game.jsonl` — 5 Llama-GM sensitivity games
- `scripts/run_gm_sensitivity.py` — small script for reproducibility (optional; inline is fine)
- Key signal confirmed: ≥1 accepted trade; 4-provider routing verified; total cost ≤$1.50
