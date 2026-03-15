# S02: RNE Prompt Architecture — UAT

**Milestone:** M001
**Written:** 2026-03-15

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is a pure library module (no UI, no HTTP). Correctness is fully expressed by the test suite (parser contract, prompt content, disclosure injection) and the smoke CLI run (end-to-end integration with real LLMs).

## Preconditions

- `.venv` activated (`source .venv/bin/activate`)
- API keys present in environment (GROQ_API_KEY, MISTRAL_API_KEY for smoke run)
- Working directory: `/Users/prajwalmishra/Desktop/Experiments/baagad-ai/research/model-family`

## Smoke Test

```bash
pytest tests/test_rne.py tests/test_rne_prompts.py -v --tb=short 2>&1 | tail -5
# → 165 passed, 1 warning
```

## Test Cases

### 1. Full test suite passes

```bash
source .venv/bin/activate
pytest tests/test_rne.py tests/test_rne_prompts.py -v
```

**Expected:** `165 passed, 1 warning` — zero failures. The single warning is a `PytestConfigWarning: Unknown config option: asyncio_mode` (harmless).

---

### 2. All 9 system prompt variants are non-empty and within token budget

```bash
python3 -c "
from src.prompts.rne_prompts import build_system_prompt
for c in ('A','B','C'):
    for f in ('neutral','social','strategic'):
        p = build_system_prompt(c, f)
        tok = len(p) // 4
        assert tok <= 300, f'{c}/{f}: {tok} tok exceeds 300'
        print(f'{c}/{f}: {tok} tok ok')
"
```

**Expected:** 9 lines printed with token counts in range 241–290. No AssertionError.

---

### 3. Disclosure injection: blind mode has no family leak; disclosed mode injects correctly

```bash
python3 -c "
from src.simulation.config import RNEConfig
from src.prompts.rne_prompts import build_round_messages

cfg_blind = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='blind', prompt_framing='neutral')
cfg_disc  = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='disclosed', prompt_framing='neutral')

blind = build_round_messages(cfg_blind, 5, 'a0', {'W':3,'S':2}, [], 'llama')
disc  = build_round_messages(cfg_disc,  5, 'a0', {'W':3,'S':2}, [], 'llama')

user_blind = blind[1]['content']
user_disc  = disc[1]['content']

assert 'llama' not in user_blind, 'FAIL: family leaked in blind mode'
assert 'llama' in user_disc, 'FAIL: family not injected in disclosed mode'
assert 'llama' not in disc[0]['content'], 'FAIL: family injected into system message'
print('disclosure injection ok')
"
```

**Expected:** `disclosure injection ok` — no assertion errors.

---

### 4. Parser handles all 4 failure modes

```bash
python3 -c "
from src.prompts.rne_prompts import parse_rne_response

# Strategy 1: direct JSON
r1 = parse_rne_response('{\"action\":\"propose\",\"give\":{\"W\":1},\"want\":{\"G\":1}}')
assert isinstance(r1, dict) and r1['action'] == 'propose', f'S1 fail: {r1}'

# Strategy 2: fenced JSON
r2 = parse_rne_response('\`\`\`json\n{\"action\":\"pass\"}\n\`\`\`')
assert isinstance(r2, dict) and r2['action'] == 'pass', f'S2 fail: {r2}'

# Strategy 3: prose-wrapped JSON
r3 = parse_rne_response('Sure! {\"action\":\"pass\"} here you go')
assert isinstance(r3, dict) and r3['action'] == 'pass', f'S3 fail: {r3}'

# Strategy 4: truncated → None
r4 = parse_rne_response('{\"action\":\"prop')
assert r4 is None, f'S4 fail: {r4}'

# Bonus: None input → None
r5 = parse_rne_response(None)
assert r5 is None, f'None fail: {r5}'

print('all 4 parser strategies ok')
"
```

**Expected:** `all 4 parser strategies ok`

---

### 5. Real Mistral×Llama smoke run completes; cost within budget

```bash
python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1

python3 -c "
import json, pathlib
summaries = sorted(pathlib.Path('data/study1').glob('*/summary.json'), key=lambda p: p.stat().st_mtime, reverse=True)
s = json.loads(summaries[0].read_text())
assert 0.0 <= s['cooperation_rate'] <= 1.0, f'M1 out of range: {s[\"cooperation_rate\"]}'
assert s['total_cost_usd'] <= 0.05, f'cost exceeded: {s[\"total_cost_usd\"]}'
print(f'smoke ok — M1={s[\"cooperation_rate\"]:.3f} cost=\${s[\"total_cost_usd\"]:.4f}')
"
```

**Expected:** Session completes 35 rounds. Summary assertion prints `smoke ok` with cost ≤ $0.05. (Trade count in a single session may be 0 — stochastic LLM behavior; this is not a failure.)

---

### 6. Mock mode runs without API calls (zero cost)

```bash
python scripts/run_rne.py \
  --family-a mistral --family-b llama \
  --condition A --disclosure blind --framing neutral --games 1 \
  --mock '{"action":"propose","give":{"W":1},"want":{"G":1}}'
```

**Expected:** Session completes instantly. No API calls. `summary.json` written to `data/study1/{session_id}/`.

## Edge Cases

### Condition C (asymmetric power) system prompt

```bash
python3 -c "
from src.prompts.rne_prompts import build_system_prompt
p = build_system_prompt('C', 'strategic')
assert 'power' in p.lower() or 'asymm' in p.lower() or 'advantage' in p.lower(), 'C/strategic missing asymmetry language'
print('C/strategic asymmetry language ok')
print(p[:200])
"
```

**Expected:** System prompt references asymmetric power dynamics. No AssertionError.

---

### Unknown condition or framing raises ValueError

```bash
python3 -c "
from src.prompts.rne_prompts import build_system_prompt
try:
    build_system_prompt('X', 'neutral')
    print('FAIL: no ValueError raised')
except ValueError as e:
    print(f'ValueError ok: {e}')

try:
    build_system_prompt('A', 'aggressive')
    print('FAIL: no ValueError raised')
except ValueError as e:
    print(f'ValueError ok: {e}')
"
```

**Expected:** Two `ValueError ok` lines.

---

### History truncation: only last 3 rounds injected

```bash
python3 -c "
from src.simulation.config import RNEConfig
from src.prompts.rne_prompts import build_round_messages

cfg = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='blind', prompt_framing='neutral')
history = ['r1: traded', 'r2: no trade', 'r3: traded', 'r4: no trade', 'r5: traded']
msgs = build_round_messages(cfg, 6, 'a0', {'W':2}, history)
user = msgs[1]['content']
assert 'r3' in user and 'r4' in user and 'r5' in user, 'last 3 not present'
assert 'r1' not in user and 'r2' not in user, 'older entries leaked'
print('history truncation ok')
"
```

**Expected:** `history truncation ok`

## Failure Signals

- Any pytest failure → check `tests/test_rne_prompts.py` class name in failure output for which module is broken
- `ValueError` from `build_system_prompt` on valid args → `_FRAMING_INTRO` or `_CONDITION_CORE` dict key mismatch
- Disclosure family name appearing in blind mode → `build_round_messages` disclosure guard broken
- `parse_rne_response` returning `None` on valid JSON → strategy 1 regex interference; check `_FENCE_RE` pattern
- Smoke run cost > $0.05 → model routing or max_tokens misconfiguration; check `PROVIDER_KWARGS` in `llm_router.py`
- `game.jsonl` missing after smoke run → `GameLogger` or directory creation bug; check `data/study1/` path

## Requirements Proved By This UAT

- R003 (RNE Prompt Architecture) — all 3 conditions × 3 framings × 2 disclosure variants produce correctly structured messages; tolerant parser handles all 4 failure modes; wired into RNERunner
- R008 (run_rne.py CLI) — CLI accepts all required arguments; produces game.jsonl, summary.json, metadata.json; mock mode works without API calls

## Not Proven By This UAT

- High trade acceptance rate in any condition — individual sessions are stochastic; behavioral signal requires Phase 0 batch (S03)
- Gemini parse reliability at scale — single-session smoke run is insufficient; Phase 0 measures per-family parse rates across 240 sessions
- M5 (min acceptable offer, Condition C) — requires Condition C sweep with asymmetric inventories; Phase 0 will surface this
- Cost at Phase 0 scale — $0.0072/session × 240 = ~$1.73 estimate; actual Phase 0 cost confirmed in S03

## Notes for Tester

- A single smoke session producing 0 accepted trades (M1=0.000) is **not a failure** — it reflects stochastic LLM behavior. The slice requirement is ≥1 trade across all sessions (prior runs contribute to this count). See T03 summary for behavioral details.
- The `1 warning` in pytest output is always `PytestConfigWarning: Unknown config option: asyncio_mode` — safe to ignore.
- `grep '"event".*"trade_executed"'` from the original slice plan **does not match** real event names. The actual event is `trade_result` with `accepted: true`. Use the python3 counting command in T03 diagnostics instead.
