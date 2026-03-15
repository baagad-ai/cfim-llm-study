# S03: Prompt Templates + Tolerant Parser — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S03 proof level is contract + integration (no real API calls required). All acceptance criteria are covered by pytest: parser correctness, token budgets, config shape, agent/gm wiring. No human behavioral judgment is needed.

## Preconditions

- `.venv` activated (or use `.venv/bin/python -m pytest` directly)
- Working directory: `research/model-family/`
- No API keys required — all tests use mock LLM responses

## Smoke Test

```bash
.venv/bin/python -c "
from src.prompts.json_utils import parse_agent_response
print(parse_agent_response('<think>r</think>\n{\"action_type\":\"hoard\"}', {}))
"
# Expected: {'action_type': 'hoard'} (with WARNING log for strategy 2 fallback)
```

## Test Cases

### 1. Full test suite (primary gate)

```bash
.venv/bin/python -m pytest tests/test_smoke.py tests/test_prompts.py -v
```

**Expected:** 23 passed (5 smoke + 18 prompts), 0 failures, 0 errors.

### 2. Phase0 config shape

```bash
.venv/bin/python -c "
from src.simulation.config import GameConfig
c = GameConfig.from_name('phase0')
fams = [e['model_family'] for e in c.agent_models]
assert len(c.agent_models) == 6
assert fams.count('llama') == 2
assert fams.count('deepseek') == 2
assert fams.count('gemini') == 1
assert fams.count('mistral') == 1
print('phase0 ok')
"
```

**Expected:** `phase0 ok`

### 3. New mono configs

```bash
.venv/bin/python -c "
from src.simulation.config import GameConfig
for name in ('llama-mono', 'deepseek-mono', 'gemini-mono'):
    cfg = GameConfig.from_name(name)
    fam = name.split('-')[0]
    assert len(cfg.agent_models) == 6
    assert all(e['model_family'] == fam for e in cfg.agent_models), name
    print(name, 'ok')
"
```

**Expected:** Three `ok` lines, one per config.

### 4. Parser edge cases — all 5 variants

```bash
.venv/bin/python -c "
from src.prompts.json_utils import parse_agent_response
# Valid JSON
assert parse_agent_response('{\"action_type\": \"hoard\"}', {}) == {'action_type': 'hoard'}
# Fenced JSON
assert parse_agent_response('\`\`\`json\n{\"action_type\": \"hoard\"}\n\`\`\`', {}) == {'action_type': 'hoard'}
# Embedded in prose
assert parse_agent_response('Here is my action: {\"action_type\": \"build\"} done.', {}) == {'action_type': 'build'}
# Truncated — must return None (not a falsy dict)
result = parse_agent_response('{\"action_type\": \"bu', {})
assert result is None, f'Expected None, got {result}'
# DeepSeek think prefix
assert parse_agent_response('<think>reasoning</think>\n{\"action_type\": \"hoard\"}', {}) == {'action_type': 'hoard'}
print('all 5 parse cases ok')
"
```

**Expected:** `all 5 parse cases ok`

### 5. Token budgets

```bash
.venv/bin/python -c "
from src.prompts.agent_action import build_act_messages
from src.prompts.trade_response import build_respond_messages
from src.simulation.config import _STANDARD_BUILDINGS
inv = {'wood':2,'stone':3,'grain':4,'clay':1,'fiber':0}
msgs = build_act_messages('a0','mistral',5,inv,6,[],{'a0':6,'a1':3},[],_STANDARD_BUILDINGS)
act_tok = sum(len(m['content']) for m in msgs) // 4
msgs2 = build_respond_messages('a0',inv,6,{'proposer':'a1','give':{'wood':1},'want':{'grain':1}},_STANDARD_BUILDINGS)
resp_tok = sum(len(m['content']) for m in msgs2) // 4
print(f'act_tok={act_tok} (≤108), respond_tok={resp_tok} (≤72)')
assert act_tok <= 108, act_tok
assert resp_tok <= 72, resp_tok
print('token budgets ok')
"
```

**Expected:** `act_tok=83 (≤108), respond_tok=66 (≤72)` and `token budgets ok`

### 6. Circular import resolution

```bash
.venv/bin/python -c "
import src.prompts
from src.prompts.json_utils import parse_agent_response, format_inventory, get_completion_kwargs
from src.simulation.agent import Agent
print('circular import ok')
"
```

**Expected:** `circular import ok` (no ImportError)

## Edge Cases

### Truncated JSON returns None (not a default dict)

```bash
.venv/bin/python -c "
from src.prompts.json_utils import parse_agent_response
result = parse_agent_response('{\"action_type\": \"bu', {})
assert result is None, f'Expected None, got {result!r}'
print('None sentinel ok')
"
```

**Expected:** `None sentinel ok` — this matters because callers use `if result is None` to trigger hoarding fallback; a falsy dict would incorrectly skip the fallback.

### Gemini kwargs exclude response_format

```bash
.venv/bin/python -c "
from src.prompts.json_utils import get_completion_kwargs
kwargs = get_completion_kwargs('gemini')
assert 'response_format' not in kwargs, f'response_format found in gemini kwargs: {kwargs}'
print('gemini no response_format ok')
"
```

**Expected:** `gemini no response_format ok` — Gemini with `response_format=json_object` produces empty responses (D021).

### Mutation isolation for completion kwargs

```bash
.venv/bin/python -c "
from src.prompts.json_utils import get_completion_kwargs
k1 = get_completion_kwargs('mistral')
k1['injected'] = True
k2 = get_completion_kwargs('mistral')
assert 'injected' not in k2, 'mutation leaked into PROVIDER_KWARGS'
print('copy isolation ok')
"
```

**Expected:** `copy isolation ok`

## Failure Signals

- `ImportError: cannot import name X from partially initialized module` → circular import resurfaced; check if `src.simulation.__init__` gained new eager imports
- Any test in `TestParseAgentResponse` failing `result is None` check → bracket-counter extraction has regressed; inspect `extract_first_json_object`
- Token budget tests failing → a prompt module was expanded; re-check that system message has no dynamic fields
- `phase0 ok` check failing with wrong family set → `_mixed_4family()` or `from_name('phase0')` lookup changed
- `TestGetCompletionKwargs` failing on gemini → `PROVIDER_KWARGS` structure changed in `llm_router.py`

## Requirements Proved By This UAT

- R003 (Cache-Optimized Prompt Templates) — prompts are implemented; static system prefix confirmed (no round/agent/inventory in system message); token targets met (84 tok act, 66 tok respond); static structure confirmed by inspection and test assertions.

## Not Proven By This UAT

- **Trade acceptance rate improvement** — D037 VP-unlock framing is in the prompt, but `≥1 accepted trade` requires real LLM calls in S04 Phase 0 calibration games.
- **Cache hit rate** — requires real API calls with prefix-stable prompts; validated in S04.
- **JSON parse success rate per provider** — requires real Gemini/DeepSeek/Llama responses; tested with synthetic variants only here.
- **End-to-end 4-family game** — `GameConfig.from_name('phase0')` config is correct, but a real 4-family game with all 4 API keys live is S04's integration gate.

## Notes for Tester

- The `asyncio_mode` warning in pytest output is harmless — it comes from `pyproject.toml` having `asyncio_mode = "auto"` without `pytest-asyncio` installed. No action needed.
- The `chars//4` token estimation is approximate. If you want exact tokenization, use `tiktoken` or the provider's tokenizer — the actual counts will likely be lower (BPE is more efficient than chars/4 for English).
- S04's first task should run `python scripts/run_game.py --config phase0 --games 1` with all 4 API keys present before running the full 30-game calibration batch.
