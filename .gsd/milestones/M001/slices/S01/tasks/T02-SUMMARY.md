---
id: T02
parent: S01
milestone: M001
provides:
  - src/simulation/rne_game.py — RNERunner with run_session(), trade mechanics, decay, perturbation
  - _proposals_compatible(), _execute_trade(), _apply_decay(), _inventory_value() utilities
  - summary.json + metadata.json written per session
  - 47 passing tests in tests/test_rne.py covering engine, mechanics, and T01 components
key_files:
  - src/simulation/rne_game.py
  - tests/test_rne.py
key_decisions:
  - D048: Engine v2 full rebuild as RNE bilateral (not Trade Island)
duration: ~2h
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T02: RNE Game Engine

**`RNERunner.run_session()` implemented. 35-round bilateral loop with simultaneous proposals, decay, perturbation, M1–M4. 47 tests pass.**

## What Was Built

`src/simulation/rne_game.py`:
- `RNERunner.run_session(config, mock_response=None)` — 35-round loop
- Simultaneous action collection → compatibility check → optional respond call → trade execution
- 10% decay: `int(qty * 0.9)` per resource per agent per round, after trade settlement
- Perturbation at `config.perturbation_round` (default 20): logs `perturbation` event
- `_compute_metrics()` computes M1–M4 post-game (see T03 summary)
- `summary.json` and `metadata.json` written to `data/study1/{session_id}/`

## Verification

```
pytest tests/test_rne.py -v → 47 passed, 1 warning
```

All `TestRNEEngine` and `TestRNEMechanics` tests pass.
