# S01: LiteLLM + Environment Setup

**Milestone:** M001
**Status:** ✅ COMPLETE (2026-03-15)
**Actual time:** ~3 hours
**Requirements:** R001

## Goal

Working Python environment with all dependencies installed, LiteLLM routing configured and verified for all 4 providers, API keys loaded and tested.

## Tasks

### T01: Python venv + base dependencies ✅
- `.venv/` created at `research/model-family/.venv/` (Python 3.14)
- `litellm`, `python-dotenv` installed
- `requirements.txt` written with full dep list + version ranges
- Full install deferred to S02 (concordia + analysis deps install alongside simulation code)

### T02: LiteLLM configuration file ✅
- `config/litellm_config.yaml` created with all 6 model entries
- Router settings: max_retries=3, retry_after=2, max_budget=$80
- Keys loaded from `.env`
- **Deviations from blueprint** (see DECISIONS.md D018-D022):
  - DeepSeek: `openrouter/deepseek/deepseek-chat` (not direct API — India payment block)
  - DeepSeek reasoner: `openrouter/deepseek/deepseek-r1`
  - Mistral: `mistral-small-2506` (not `3.1-2503` — unavailable on account)
  - Gemini: no `response_format json_object`; `max_tokens=200`; thinking disabled in code

### T03: API key collection + .env setup ✅
- Keys collected via secure_env_collect:
  - `GROQ_API_KEY` ✅
  - `OPENROUTER_API_KEY` ✅ (replaces DEEPSEEK_API_KEY — India constraint)
  - `GOOGLE_API_KEY` ✅ (paid tier — billing enabled on GCP project)
  - `MISTRAL_API_KEY` ✅
- `.env` written, in `.gitignore`
- `.env.example` template committed

### T04: Provider connectivity test ✅
- `scripts/test_connectivity.py` written and passing
- All 4 providers verified:
  - Groq/Llama 3.3 70B: json_object mode, 65in/17out, $0.000052
  - OpenRouter/DeepSeek V3: json_object mode, 17in/11out, $0.000015
  - Gemini 2.5 Flash: thinking=None confirmed, 10in/10out, $0.000028
  - Mistral Small 2506: json_object mode, 17in/11out, $0.000000
- Key Gemini finding: `thinking={'type':'disabled','budget_tokens':0}` is the only method
  that fully zeros reasoning tokens. `thinking={'type':'disabled'}` alone still burns ~25 tokens.
  Paid tier required (free tier: 20 req/day hard limit on gemini-2.5-flash).

### T05: Project structure scaffold ✅
- Created: `src/{simulation,prompts,analysis,scripts}/`, `data/{raw,processed,phase0,phase1,phase2/}`, `config/`, `tests/`, `notebooks/`
- `README.md` written
- Analysis stubs (H1-H4) committed — pre-registration ready
- Git repo initialized, 3 commits

## Acceptance Criteria

- [x] `python scripts/test_connectivity.py` → 4 green checks ✅
- [x] JSON mode verified per-provider (per-provider workarounds documented) ✅
- [x] Cost tracking: <$0.001 burned during connectivity tests ✅
- [x] `.venv/` active, litellm + python-dotenv imports work ✅
- [x] `requirements.txt` committed ✅
- [x] `.env` in `.gitignore`, `.env.example` committed ✅

## Deviations from Blueprint (all in DECISIONS.md)

| Item | Blueprint | Actual | Decision |
|---|---|---|---|
| DeepSeek API | Direct DeepSeek API | OpenRouter proxy | D019 |
| DeepSeek model ID | `deepseek/deepseek-chat` | `openrouter/deepseek/deepseek-chat` | D019 |
| Mistral version | `mistral-small-3.1-2503` | `mistral-small-2506` | D018 |
| Gemini JSON mode | `response_format json_object` | No JSON mode, fence stripper | D021 |
| Gemini thinking | `thinking_budget=0` via config | `thinking={'type':'disabled','budget_tokens':0}` in code | D020 |
| Gemini max_tokens | 150 | 200 | D022 |
| Gemini key tier | Paid (assumed) | Free tier → upgraded to paid | D021 |

## What S02 Must Know

- Gemini calls need `thinking={'type':'disabled','budget_tokens':0}` and `max_tokens=200` in **every** completion call
- Gemini responses may have markdown fences — strip before JSON parse
- DeepSeek `json_object` mode works via OpenRouter — no schema-in-prompt workaround needed (tested)
- LiteLLM `drop_params=True` must be set globally to handle per-provider param differences silently
