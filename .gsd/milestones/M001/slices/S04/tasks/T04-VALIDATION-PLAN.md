---
estimated_steps: 4
estimated_files: 0
---

# T04-VALIDATION: 5-Game Validation Run

**Slice:** S04 — Phase 0 Calibration (30 games)
**Milestone:** M001
**Depends on:** T03-FIX complete (`pytest tests/ -v` all pass)

## Description

Before spending $1.50 on 30 calibration games, run 5 real games to confirm the repair sprint (T03-FIX) actually fixed the simulation. The key signals are VP range (should be 3–9, not −17 to −20) and trade acceptance rate (should be >10%, not 0%).

This is a go/no-go gate: if the validation run still shows starvation-floor VP or 0% acceptance, stop and return to T03-FIX rather than burning budget on invalid data.

Wall time: ~15–20 minutes for 5 games.

## Steps

1. **Run 5 phase0 games:**
   ```bash
   python scripts/run_game.py --config phase0 --games 5
   ```

2. **Check VP range:**
   ```bash
   GAMES=$(ls -t data/raw | head -5)
   for gid in $GAMES; do
     jq 'select(.event=="round_end" and .round==25) | {agent_id, vp}' data/raw/$gid/game.jsonl
   done
   ```
   Expected: VP values in range 3–9. Red flag: any agent at −17 to −20 (starvation floor).

3. **Check trade acceptance rate:**
   ```bash
   proposals=$(grep -c '"action_type": "trade"' data/raw/*/game.jsonl 2>/dev/null || echo 0)
   accepted=$(grep -c '"accepted": true' data/raw/*/game.jsonl 2>/dev/null || echo 0)
   echo "Proposals: $proposals, Accepted: $accepted"
   python3 -c "p=$proposals; a=$accepted; print(f'Rate: {a/p*100:.1f}%' if p > 0 else 'No proposals')"
   ```
   Expected: >10% acceptance. Red flag: 0% (same as before repair).

4. **Check for starvation events and build successes:**
   ```bash
   grep '"event": "grain_consumption"' data/raw/*/game.jsonl | grep '"starved": true' | wc -l
   # Some starvation is acceptable; systematic starvation (every agent, every game) is not.
   
   grep '"event": "build"' data/raw/*/game.jsonl | wc -l
   grep '"event": "build_failed"' data/raw/*/game.jsonl | wc -l
   # Expect: some successful builds. build_success_rate > 20% is healthy.
   ```

## Pass/Fail Criteria

| Signal | Pass | Fail → Action |
|---|---|---|
| VP range at round 25 | 3–9 for majority of agents | Any agent ≤ −10 → return to T03-FIX |
| Trade acceptance rate | >10% of proposals | 0% or <5% → return to T03-FIX |
| Build successes | ≥1 per 5 games | 0 builds → return to T03-FIX |
| Cost per game | ≤$0.10 | >$0.15 → investigate R1 overrun |

## Must-Haves

- [ ] VP range: majority of agents at round 25 have VP ≥ 0
- [ ] Trade acceptance: ≥5 accepted trades across 5 games (>10% of ~150 proposals)
- [ ] ≥1 building per game on average
- [ ] Total cost for 5 games ≤$0.50

## Verification

```bash
# VP positive for majority
jq 'select(.event=="round_end" and .round==25) | .vp' data/raw/*/game.jsonl | \
  python3 -c "import sys; vs=[int(l) for l in sys.stdin]; \
  pos=sum(1 for v in vs if v>=0); \
  print(f'{pos}/{len(vs)} agents ended positive VP')"
# → majority positive

# Trade acceptance
grep '"accepted": true' data/raw/*/game.jsonl | wc -l
# ≥ 5
```

## Inputs

- T03-FIX complete: all CF+SF issues resolved, pytest all pass
- `.env` with all 4 API keys

## Expected Output

- 5 game JSONL files in `data/raw/`
- Validation signal: VP range and trade acceptance confirm simulation is fixed
- Go/no-go decision: proceed to T05 (30-game run) or return to T03-FIX
