# S01: LiteLLM + Environment Setup

**Milestone:** M001
**Status:** ⬜ planned
**Estimated time:** 3-4 hours
**Requirements:** R001

## Goal

Working Python environment with all dependencies installed, LiteLLM routing configured and verified for all 4 providers, API keys loaded and tested.

## Tasks

### T01: Python venv + base dependencies
- Create `.venv/` in `research/model-family/`
- Install: `litellm`, `concordia-ai` (Concordia v2.0), `polars`, `statsmodels`, `scikit-learn`, `networkx`, `sentence-transformers`, `seaborn`, `matplotlib`, `pydantic`, `python-dotenv`, `pytest`, `jupyter`
- Pin all versions in `requirements.txt`
- Verify: `python -c "import litellm; import concordia; print('ok')"` passes

### T02: LiteLLM configuration file
- Create `config/litellm_config.yaml` with all 6 model entries (llama-70b, deepseek-chat, deepseek-reasoner, gemini-flash, mistral-small, gm) per blueprint §1
- Add router settings: max_retries=3, retry_after=2, max_budget=$80
- Load API keys from `.env` (not hardcoded)

### T03: API key collection + .env setup
- Collect all 4 API keys via secure_env_collect:
  - GROQ_API_KEY
  - DEEPSEEK_API_KEY
  - GOOGLE_API_KEY
  - MISTRAL_API_KEY
- Create `.env` template and add to `.gitignore`

### T04: Provider connectivity test
- Write `scripts/test_connectivity.py`
- Send minimal ping call to each provider (1 token in, 1 token out)
- Verify JSON mode works for: Groq (json_schema), Gemini (responseJsonSchema), DeepSeek (json_object + schema in prompt), Mistral (json_object + schema in prompt)
- Log cost per call, verify budget tracking works
- Expected output: 4 green checks, cost ~$0.001

### T05: Project structure scaffold
- Create directory structure:
  ```
  src/
    simulation/      # Trade Island + Concordia integration
    prompts/         # Prompt templates
    analysis/        # Analysis scripts (pre-registration stubs)
    scripts/         # Runner scripts
  data/
    raw/             # JSONL game logs
    processed/       # Polars dataframes
    phase0/
    phase1/
    phase2/
  config/
  tests/
  notebooks/
  ```
- Create `README.md` with project overview

## Acceptance Criteria

- [ ] `python scripts/test_connectivity.py` → 4 green checks, all providers responding
- [ ] JSON mode verified per-provider (right schema enforcement for each)
- [ ] Cost tracking: budget tracker shows <$0.01 burned after connectivity test
- [ ] `.venv/` active, all imports work
- [ ] `requirements.txt` committed with pinned versions
- [ ] `.env` in `.gitignore`, template `.env.example` committed

## Notes

- DeepSeek: use `deepseek-chat` model ID, NOT `deepseek-reasoner` for agent calls
- Gemini: `thinking_budget: 0` is set in code, not just config — verify this works
- Mistral: pin to `mistral-small-3.1-2503` exact version, NOT `mistral-small-latest`
- Groq: automatic prompt caching — no configuration needed, verify cache hit reporting in response headers
