---
id: T01
parent: S02
milestone: M001
provides:
  - pytest, polars, scipy, statsmodels, scikit-learn, networkx, seaborn installed and importable
  - GameConfig Pydantic model with from_name() factory (mistral-mono, phase0, pairwise-{A}-{B})
  - GameLogger JSONL writer with log(), flush(), log_round_end() — "vp" field name enforced
  - requirements-lock.txt updated with exact pinned versions and sentence-transformers note
key_files:
  - src/simulation/config.py
  - src/simulation/logger.py
  - src/simulation/__init__.py
  - requirements-lock.txt
key_decisions:
  - buffering=1 (line buffering) on the logger file handle so each log() call is immediately readable on disk without explicit flush() — supports crash-resume and real-time jq inspection
  - pairwise config parses "pairwise-{A}-{B}" by splitting on "-" (family names must be single words); agents a0-a2 are family A, a3-a5 are family B
  - phase0 is a mistral-mono placeholder — documented in code with a comment pointing to S03 for real model mix
  - sentence-transformers excluded; compatibility with Python 3.14 unverified — commented in requirements-lock.txt with S03/S04 flag
patterns_established:
  - Named config factory pattern: GameConfig.from_name(name) as the single entry point for all config variants; unknown names raise ValueError with valid options listed
  - GameLogger as append-only context manager; flush()/fsync() available for explicit durability checkpoints
  - "vp" is the canonical field name for victory points throughout the codebase
observability_surfaces:
  - Every log() line includes ts (ISO8601 UTC), event, game_id — grep/jq-friendly
  - flush() + fsync() available for checkpoint writes between rounds
duration: ~20 min
verification_result: passed
completed_at: 2026-03-15
blocker_discovered: false
---

# T01: Install deps, write config.py and logger.py

**Installed 7 analysis packages, implemented GameConfig with named-config factory, and GameLogger with enforced "vp" field name — all three plan verification commands pass.**

## What Happened

Activated the Python 3.14.3 venv and installed: pytest 9.0.2, polars 1.39.0, scipy 1.17.1, statsmodels 0.14.6, scikit-learn 1.8.0, networkx 3.6.1, seaborn 0.13.2. Froze to requirements-lock.txt and appended a comment documenting why sentence-transformers was excluded (torch/Python 3.14 wheel compatibility unverified; flagged for S03/S04 boundary check).

`GameConfig` uses Pydantic v2 BaseModel with a `from_name()` class method. The pairwise factory parses `"pairwise-{A}-{B}"` by splitting on `-`; agents a0–a2 take family A, a3–a5 take family B. The `_MODEL_REGISTRY` dict maps family short-names to litellm model strings and provider kwargs — keeps config self-contained and easy to extend.

`GameLogger` opens the JSONL file with `buffering=1` (line-buffered), meaning each `log()` call lands on disk immediately without requiring an explicit `flush()`. The `flush()` method still exists and calls `fsync()` for guaranteed durability at checkpoint boundaries. `log_round_end()` emits one line per agent with the flat schema `{game_id, model_family, round, agent_id, vp}`.

One issue caught during verification: the original `open()` call used default block buffering, which caused the exact plan verification command (which reads the file without calling `flush()`) to see an empty file. Fixed by switching to `buffering=1`.

## Verification

All three plan verification commands pass verbatim:

```
# imports
python -c "import pytest, polars, scipy, statsmodels, sklearn, networkx, seaborn; print('all ok')"
→ all ok

# config
python -c "from src.simulation.config import GameConfig; c = GameConfig.from_name('mistral-mono'); assert c.num_rounds == 25; assert len(c.agent_models) == 6; print('config ok')"
→ config ok

# logger
python -c "from src.simulation.logger import GameLogger; import tempfile, json, pathlib; d=pathlib.Path(tempfile.mkdtemp()); lg=GameLogger('test123', d); lg.log_round_end(1, [{'agent_id':'a0','model_family':'mistral','vp':3}]); lines=[json.loads(l) for l in (d/'game.jsonl').read_text().splitlines()]; assert lines[0]['vp']==3; assert lines[0]['event']=='round_end'; print('logger ok')"
→ logger ok
```

Additional checks confirmed:
- `pairwise-llama-mistral` → 3 llama agents + 3 mistral agents ✓
- All 3 buildings (Market, Granary, Tower) present with vp=3 ✓
- `from src.simulation import GameConfig, GameLogger` works ✓
- `requirements-lock.txt` tail contains sentence-transformers exclusion comment ✓

## Diagnostics

```bash
# Inspect any game.jsonl in real-time
jq '.event' data/raw/*/game.jsonl | sort | uniq -c

# Verify vp field name in output
grep '"vp"' data/raw/*/game.jsonl | head -1

# Check config is correct before a run
python -c "from src.simulation.config import GameConfig; import json; c = GameConfig.from_name('mistral-mono'); print(json.dumps(c.model_dump(), indent=2))"
```

## Deviations

- Added `buffering=1` to the logger file open call (not in original plan spec). Required to make each `log()` immediately readable on disk without explicit `flush()`. The plan verification command reads the file without flushing, so this was necessary for correctness.

## Known Issues

None.

## Files Created/Modified

- `src/simulation/config.py` — GameConfig Pydantic model with from_name() factory; _MODEL_REGISTRY for model string lookup
- `src/simulation/logger.py` — GameLogger with log(), flush(), close(), log_round_end(); line-buffered file handle
- `src/simulation/__init__.py` — exports GameConfig, GameLogger
- `requirements-lock.txt` — full pip freeze output + sentence-transformers exclusion comment
