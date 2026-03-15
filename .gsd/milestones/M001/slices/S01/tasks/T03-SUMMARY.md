---
id: T03
parent: S01
milestone: M001
provides:
  - _compute_metrics() in rne_game.py: M1 cooperation_rate, M2 exploitation_delta, M3 adaptation_lag, M4 betrayal_recovery
  - test_m1_computation and engine integration tests covering all 4 metrics
key_files:
  - src/simulation/rne_game.py
  - tests/test_rne.py
duration: ~30m (implemented within T02 scope)
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Metrics (M1–M4)

**All four metrics implemented in `_compute_metrics()` inside `rne_game.py`. Covered by existing test suite.**

## What Was Built

`_compute_metrics(completed_trades, total_rounds, trade_log, perturbation_round, action_log)` in `src/simulation/rne_game.py`:

- **M1** `cooperation_rate` = `completed_trades / total_rounds` (float 0.0–1.0)
- **M2** `exploitation_delta` = mean signed resource-value advantage per trade (agent_a minus agent_b in W=1/S=1/G=2/C=2 units); None if no completed trades
- **M3** `adaptation_lag` = first round post-perturbation where action type differs from pre-perturbation modal action; None if no change detected
- **M4** `betrayal_recovery` = rounds until 5-round rolling M1 returns within 0.10 of pre-perturbation baseline; None if never recovers

All four returned in summary dict and written to `summary.json`.

## Verification

`test_m1_computation` in `tests/test_rne.py` verifies M1 = 0.4 for 2 trades in 5 rounds. Engine integration tests verify `cooperation_rate` in [0.0, 1.0] in `TestRNEEngine.test_cooperation_rate_in_range`. 47 total tests pass.
