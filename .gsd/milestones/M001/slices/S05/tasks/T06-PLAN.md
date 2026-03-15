# T06: Integration Tests + 5-Game Validation

**Slice:** S05 — Simulation Engine v2
**Status:** ⬜ Not started
**Est:** 1h code + 30m wall-clock

## Goal

Full integration test suite covering all v2 mechanics. Then run 5 live phase0 games to confirm: VP 3–9, trade acceptance >15%, broadcast/spoilage/production events present.

## Files
- Create/complete: `tests/test_mechanics_v2.py`
- Modify: `tests/test_smoke.py` — update for v2 event schema
- Optional: `scripts/run_game.py` — --dashboard flag

## Integration Test Checklist

```python
# tests/test_mechanics_v2.py — full suite

# GameConfig v2
def test_config_v2_defaults(): ...
def test_config_win_vp_10(): ...

# Economy
def test_passive_production(): ...
def test_hoard_bonus_production(): ...
def test_spoilage_caps_grain(): ...
def test_spoilage_caps_fiber(): ...
def test_no_spoilage_for_wood(): ...
def test_destitution_triggers(): ...
def test_destitution_not_triggered(): ...

# Broadcast
def test_broadcast_returns_want(): ...
def test_market_board_in_game_state(): ...
def test_act_shows_market_board(): ...

# Prompts
def test_rules_block_complete(): ...
def test_respond_system_static(): ...
def test_act_includes_specialty(): ...
def test_reflection_json_output(): ...

# Observability
def test_round_metrics_logged(): ...
def test_round_end_has_inventory(): ...
def test_short_term_memory_3_round_window(): ...

# Gift action
def test_gift_transfers_resources(): ...
def test_gift_without_resources_does_nothing(): ...

# End-to-end mock game
def test_full_mock_game_v2_25_rounds():
    # Run a 25-round mock game using mock_response
    # Verify: round_metrics events present (25 total)
    # Verify: no crashes
    # Verify: final VP >= 0 (not -17 to -20)
    # Verify: broadcast events present (6 per round × 25 = 150 total)
    ...
```

## 5-Game Validation Commands

```bash
# Run 5 phase0 games
python scripts/run_game.py --config phase0 --games 5

# Check VP range
for gid in $(ls -t data/raw | head -5); do
  jq 'select(.event=="game_end") | .winner_vp' data/raw/$gid/game.jsonl
done
# Expected: values 3–9 (not negative)

# Check trade acceptance
grep '"accepted": true' data/raw/*/game.jsonl | wc -l
# Expected: ≥ 7 (>15% of ~50 proposals across 5 games)

# Check new events present
grep '"event":"broadcast"' data/raw/*/game.jsonl | head -3
grep '"event":"spoilage"' data/raw/*/game.jsonl | head -3
grep '"event":"production"' data/raw/*/game.jsonl | head -3
grep '"event":"round_metrics"' data/raw/*/game.jsonl | head -3

# Check round_end has inventory
jq 'select(.event=="round_end") | .inventory' data/raw/$(ls -t data/raw | head -1)/game.jsonl | head -5
# Expected: {"wood": N, "stone": N, ...} dict for each round_end

# Check cost per game
for gid in $(ls -t data/raw | head -5); do
  jq 'select(.event=="game_end") | .total_cost_usd' data/raw/$gid/game.jsonl
done
# Expected: each ≤ $0.30
```

## Done When
- `pytest tests/ -v` — 0 failures (all tests including v2 suite)
- 5 live games show VP 3–9
- Trade acceptance > 15% confirmed
- All new event types present in JSONL
- Commit: `feat: S05 complete — simulation engine v2 validated (5-game run)`
- Update S05-PLAN.md task checkboxes
- Update STATE.md: next action = S06 (OSF pre-registration)
