---
estimated_steps: 4
estimated_files: 2
---

# T02: Round messages + disclosure injection

**Slice:** S02 — RNE Prompt Architecture
**Milestone:** M001

## Description

Write `build_round_messages(config, round_num, agent_id, inventory, history, opponent_family=None)` that returns the `list[dict]` messages for each round's LLM call. When `config.disclosure == "disclosed"`, inject the opponent's model family name into the user message.

## Steps

1. Add `build_round_messages(...)` to `src/prompts/rne_prompts.py`
2. User message includes: round number, agent's current inventory (W/S/G/C values), recent trade history (last 3 rounds), and opponent family name if disclosed
3. When `config.disclosure == "blind"`: no opponent family info in message
4. When `config.disclosure == "disclosed"`: include `"Your opponent is a {opponent_family} model."` in user message
5. Wire into `RNERunner.run_session()` replacing the current raw message construction

## Must-Haves

- [ ] Returns `list[dict]` with at least one `{"role": "system", "content": ...}` and one `{"role": "user", "content": ...}`
- [ ] Blind condition: opponent family name NOT present in any message content
- [ ] Disclosed condition: opponent family name present in user message content
- [ ] History injection: last ≤3 rounds of trade outcomes included
- [ ] Token count (system + user combined) ≤ 400 tokens for any combination

## Verification

```bash
source .venv/bin/activate
python3 -c "
from src.simulation.config import RNEConfig
from src.prompts.rne_prompts import build_round_messages

cfg_blind = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='blind', prompt_framing='neutral')
cfg_disc  = RNEConfig(family_a='mistral', family_b='llama', condition='A', disclosure='disclosed', prompt_framing='neutral')

msgs_blind = build_round_messages(cfg_blind, round_num=5, agent_id='a0', inventory={'W':3,'S':2,'G':1,'C':1}, history=[], opponent_family='llama')
msgs_disc  = build_round_messages(cfg_disc,  round_num=5, agent_id='a0', inventory={'W':3,'S':2,'G':1,'C':1}, history=[], opponent_family='llama')

all_blind = ' '.join(m['content'] for m in msgs_blind)
all_disc  = ' '.join(m['content'] for m in msgs_disc)
assert 'llama' not in all_blind, 'blind leaked family name'
assert 'llama' in all_disc, 'disclosed missing family name'
print('disclosure injection ok')
"
```

## Expected Output

- `src/prompts/rne_prompts.py` — updated with `build_round_messages`
- `src/simulation/rne_game.py` — updated to call `build_round_messages`
