---
estimated_steps: 5
estimated_files: 2
---

# T01: System prompt variants — 3 conditions × 3 framings

**Slice:** S02 — RNE Prompt Architecture
**Milestone:** M001

## Description

Write `build_system_prompt(condition, framing)` returning the static system message for each of the 9 (condition × framing) combinations. These are the cache-able prefixes that every round reuses. Wire the function into `RNERunner` so it's called once per session at session start.

## Steps

1. Create `src/prompts/rne_prompts.py`
2. Define 3 condition descriptions (A: coordination — pure gains from trade, B: mixed-motive — asymmetric endowments create exploitation opportunity, C: asymmetric power — one agent controls a scarce high-value resource)
3. Define 3 framing variants (neutral: plain mechanics description, social: cooperative/relationship framing, strategic: competitive/utility framing)
4. Implement `build_system_prompt(condition: str, framing: str) -> str` — raises `ValueError` on unknown condition/framing; result cached with `@functools.lru_cache`
5. Wire into `RNERunner.run_session()`: call `build_system_prompt(config.condition, config.prompt_framing)` once at session start; pass as system message in every `call_llm` call

## Must-Haves

- [ ] `build_system_prompt` returns a non-empty string for all 9 (A/B/C × neutral/social/strategic) combinations
- [ ] Raises `ValueError` for unknown condition or framing
- [ ] Result is deterministic (same inputs → same output, every call)
- [ ] Token count for any variant ≤ 300 tokens (rough: len(text)//4)
- [ ] `RNERunner` passes system prompt in messages list to `call_llm`

## Verification

```bash
source .venv/bin/activate
python3 -c "
from src.prompts.rne_prompts import build_system_prompt
for cond in ('A','B','C'):
    for framing in ('neutral','social','strategic'):
        s = build_system_prompt(cond, framing)
        assert len(s) > 50, f'{cond}/{framing} too short'
        assert len(s)//4 <= 300, f'{cond}/{framing} too long: {len(s)//4} tok'
        print(f'{cond}/{framing}: {len(s)//4} tok ok')
"
```

## Inputs

- `.gsd/SIMULATION_DESIGN.md` §3.1 — condition descriptions
- `src/simulation/rne_game.py` — `RNERunner` call sites

## Expected Output

- `src/prompts/rne_prompts.py` — with `build_system_prompt`
- `src/simulation/rne_game.py` — updated to use system prompt
