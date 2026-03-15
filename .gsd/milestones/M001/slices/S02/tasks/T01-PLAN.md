---
estimated_steps: 6
estimated_files: 4
---

# T01: Install deps, write config.py and logger.py

**Slice:** S02 — Trade Island Engine
**Milestone:** M001

## Description

Install all analysis/test dependencies (pytest, polars, scipy, etc.) so subsequent tasks can write and run tests. Then implement `GameConfig` (Pydantic model with named-config factory) and `GameLogger` (JSONL writer with flat `round_end` schema). These two modules are the schema contract that every other S02 module references — locking them first prevents field-name drift.

## Steps

1. Activate `.venv` and install: `pip install pytest polars scipy statsmodels scikit-learn networkx seaborn`. Do NOT install `sentence-transformers` yet — add a comment in `requirements-lock.txt` noting torch wheel compatibility with Python 3.14 is unverified; flag for S03/S04 boundary check.
2. Run `pip freeze > requirements-lock.txt` from the project root.
3. Verify imports work: `python -c "import pytest, polars, scipy, statsmodels, sklearn, networkx, seaborn; print('all ok')"`.
4. Write `src/simulation/config.py`: `GameConfig` as a Pydantic `BaseModel`. Fields: `config_name: str`, `num_agents: int = 6`, `num_rounds: int = 25`, `resources: list[str]` (default: `["wood","stone","grain","clay","fiber"]`), `buildings: dict[str, dict]` (name → `{cost: dict, vp: int}`), `hunger_rate: int = 1` (grain consumed per agent per round), `gm_model: str`, `agent_models: list[dict]` (one entry per agent: `{agent_id, model_family, model_string, provider_kwargs}`). Add class method `from_name(name: str) -> GameConfig` returning configs for `"mistral-mono"` (all 6 agents on `mistral/mistral-small-2506`), `"phase0"` (TBD mix, placeholder using mistral-mono for now), `"pairwise-{A}-{B}"` (parse the string, 3 agents each). Include 3 standard buildings: `Market` (cost: 2 wood + 2 stone, vp: 3), `Granary` (cost: 3 grain + 1 wood, vp: 3), `Tower` (cost: 2 stone + 2 clay, vp: 3) — equal VP per D006.
5. Write `src/simulation/logger.py`: `GameLogger(game_id: str, output_dir: Path)` with `log(event: str, **fields)` method that serializes `{"ts": ISO8601, "event": event, "game_id": game_id, **fields}` as a JSON line, appends to `output_dir/game.jsonl`. Add `flush()` method that calls `file.flush(); os.fsync(file.fileno())`. Add `log_round_end(round_num, agents)` helper that emits **one line per agent** with flat fields `game_id`, `model_family`, `round`, `agent_id`, `vp` — field name is literally `"vp"` not `"victory_points"`.
6. Update `src/simulation/__init__.py` to export `GameConfig` and `GameLogger`.

## Must-Haves

- [ ] `pytest`, `polars`, `scipy` all importable after step 3
- [ ] `GameConfig.from_name('mistral-mono')` returns a config with `num_rounds=25`, `num_agents=6`, all 6 `agent_models` pointing to `mistral/mistral-small-2506`
- [ ] `GameConfig.from_name('pairwise-llama-mistral')` returns 3 Llama agents + 3 Mistral agents
- [ ] `GameLogger.log_round_end()` emits one JSON line per agent with `"vp"` (not `"victory_points"`) and `game_id` present
- [ ] `requirements-lock.txt` updated with exact pinned versions
- [ ] `sentence-transformers` absence is documented with a comment in `requirements-lock.txt`

## Verification

- `python -c "import pytest, polars, scipy, statsmodels, sklearn, networkx, seaborn; print('all ok')"` exits 0
- `python -c "from src.simulation.config import GameConfig; c = GameConfig.from_name('mistral-mono'); assert c.num_rounds == 25; assert len(c.agent_models) == 6; print('config ok')"` prints `config ok`
- `python -c "from src.simulation.logger import GameLogger; import tempfile, json, pathlib; d=pathlib.Path(tempfile.mkdtemp()); lg=GameLogger('test123', d); lg.log_round_end(1, [{'agent_id':'a0','model_family':'mistral','vp':3}]); lines=[json.loads(l) for l in (d/'game.jsonl').read_text().splitlines()]; assert lines[0]['vp']==3; assert lines[0]['event']=='round_end'; print('logger ok')"` prints `logger ok`

## Inputs

- `.venv/` — Python virtual environment from S01 (all S01 packages installed)
- `config/litellm_config.yaml` — model string references for named configs
- `src/simulation/__init__.py` — empty file ready for exports

## Expected Output

- `src/simulation/config.py` — `GameConfig` Pydantic model with `from_name()` factory
- `src/simulation/logger.py` — `GameLogger` with `log()`, `flush()`, `log_round_end()` 
- `src/simulation/__init__.py` — exports `GameConfig`, `GameLogger`
- `requirements-lock.txt` — updated with all pinned versions
