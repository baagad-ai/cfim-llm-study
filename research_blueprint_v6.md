# RESEARCH BLUEPRINT v6
# Pairwise Behavioral Signatures of LLM Families in Economic Simulation

---

## Paper Identity

**Title:** *"Pairwise Behavioral Signatures: How Model Family Shapes Multi-Agent Economic Cooperation and Competition"*

**Target Venues:**
- **Primary (fast track):** NeurIPS 2026 Foundation Models Workshop (~September 2026 deadline)
- **Primary (full paper):** AAMAS 2027 (~October 2026 deadline)
- **Backup:** AAAI 2027 (~September 2026 deadline)

**Two Contributions:**
1. First complete pairwise interaction matrix of 4 model families in economic simulation, revealing matchup-specific cooperation, competition, and exploitation patterns that are invisible in monoculture studies
2. Controlled persona-vs-architecture experiment demonstrating model family drives more behavioral variation than prompt engineering

---

## 1. Models: 4 Families, All-Paid, Verified Pricing

| # | Model | Provider | Input $/1M | Output $/1M | Cache Hit $/1M | Role |
|---|---|---|---|---|---|---|
| 1 | **Llama 3.3 70B** | Groq | $0.59 | $0.79 | $0.30 (prompt cache) | Agent |
| 2 | **DeepSeek V3.2** (chat mode) | DeepSeek API | $0.28 | $0.42 | $0.028 (auto cache) | Agent |
| 2R | **DeepSeek V3.2** (reasoner mode) | DeepSeek API | $0.28 | $0.42 | $0.028 (auto cache) | DeepSeek reflection only |
| 3 | **Gemini 2.5 Flash** | Google AI Studio Paid | $0.30 | $2.50 | ~$0.075 (context cache) | Agent |
| 4 | **Mistral Small 3.1** | Mistral La Plateforme | $0.10 | $0.30 | N/A | Agent + GM |

*All prices verified against official provider documentation, March 15, 2026.*

### Key Pricing Changes from v5

1. **DeepSeek unified pricing:** Both `deepseek-chat` and `deepseek-reasoner` now use V3.2 at identical per-token rates ($0.28/$0.42). The old R1 pricing ($0.55/$2.19) no longer applies. Reasoner mode generates more output tokens (thinking chains, up to 64K) but at the same rate.

2. **Mistral corrected:** $0.10/$0.30, not $0.20/$0.60. The higher pricing belongs to Codestral/Saba models.

3. **Groq caching:** Automatic prompt caching gives 50% discount on cached input tokens. No configuration needed — identical prefixes are cached automatically.

### Why These 4 Families (Not Newer Models)

Llama 4 Scout/Maverick, Gemini 3 Flash, Mistral Small 3.2, and DeepSeek V3.2-Speciale are all available but were deliberately excluded. The study examines model FAMILIES, not versions. The selected models are established, well-characterized representatives of 4 architecturally distinct families (dense transformer, MoE, hybrid-reasoning Flash, small efficient model). Newer versions are noted as future work.

### Provider Setup (via LiteLLM)

```yaml
model_list:
  - model_name: llama-70b
    litellm_params:
      model: groq/llama-3.3-70b-versatile
      api_key: os.environ/GROQ_API_KEY
      max_tokens: 150
      response_format: {"type": "json_object"}
  - model_name: deepseek-chat
    litellm_params:
      model: deepseek/deepseek-chat
      api_key: os.environ/DEEPSEEK_API_KEY
      max_tokens: 150
      response_format: {"type": "json_object"}
  - model_name: deepseek-reasoner
    litellm_params:
      model: deepseek/deepseek-reasoner
      api_key: os.environ/DEEPSEEK_API_KEY
      max_tokens: 300
      # No JSON mode - reasoner uses thinking chains
  - model_name: gemini-flash
    litellm_params:
      model: gemini/gemini-2.5-flash
      api_key: os.environ/GOOGLE_API_KEY
      max_tokens: 150
      response_format: {"type": "json_object"}
      # CRITICAL: Disable thinking mode in code layer (thinking_budget=0)
      # to prevent 5-12x output token inflation from hidden reasoning
  - model_name: mistral-small
    litellm_params:
      model: mistral/mistral-small-3.1-2503
      # Pinned to specific version, NOT mistral-small-latest
      api_key: os.environ/MISTRAL_API_KEY
      max_tokens: 150
      response_format: {"type": "json_object"}
  - model_name: gm
    litellm_params:
      model: mistral/mistral-small-3.1-2503
      api_key: os.environ/MISTRAL_API_KEY
      max_tokens: 200
      response_format: {"type": "json_object"}

router_settings:
  retry_policy:
    max_retries: 3
    retry_after: 2
  budget_config:
    max_budget: 80  # USD hard cap
```

---

## 2. Token Engineering: Compact Prompts with Cache Optimization

### 2.1 Prompt Architecture: Prefix-First for Cache Hits

All prompts follow a strict prefix-first structure to maximize automatic caching on DeepSeek (90% discount) and Groq (50% discount):

```
[STATIC PREFIX — identical across all calls of this type, cached automatically]
System rules, building recipes, resource types, JSON output schema

[SEMI-STATIC — changes once per round]
Round number

[DYNAMIC — changes every call]
Agent inventory, recent events, reflection summary
```

Estimated cache hit rate: 60-70% of input tokens.

### 2.2 Agent Action Prompt (Optimized: ~90 tokens input)

```
TRADE ISLAND RULES | 6 agents, 25 rounds, first to 12VP wins.
BUILD: House(W2+S2=3vp) Prov(G2+Wo2=2vp) Tools(O2+C2=4vp)
Eat 1G/rnd. 0G=damage.
Output JSON: {"act":"trade|build|wait","target":"a1-a6","give":"[r][n]","want":"[r][n]"}
---
R{round}/25 | You:A{id} Specialty:{res} | VP:{vp}/12
INV: W{w} S{s} G{g} Wo{wo} O{o} C{c}
Recent: {last_3_events_compressed}
Notes: {reflection_summary_compressed}
```

### 2.3 Trade Response Prompt (~60 tokens input)

```
TRADE ISLAND | Accept/counter/reject trades.
Output JSON: {"accept":true|false,"counter":null|{"give":"[r][n]","want":"[r][n]"}}
---
A{proposer} offers you {give_res}{give_n} for your {want_res}{want_n}.
Your INV: W{w} S{s} G{g} Wo{wo} O{o} C{c} | VP:{vp}/12 R{round}/25
```

### 2.4 GM Resolution Prompt (~120 tokens input)

```
TRADE ISLAND GM | Validate trades. Check sufficient resources, no double-spending.
Output JSON: {"valid":[bool,...],"reason":["ok"|"error description",...]}
---
RESOLVE TRADES R{round}:
{list_of_accepted_trades_as_compact_tuples}
Current inventories: {agent_inventory_matrix}
```

### 2.5 Reflection Prompt (Every 5 rounds, using agent's OWN model family)

```
You are A{id} on Trade Island. Summary of rounds {start}-{end}:
{compressed_event_log}
Your current position: VP:{vp} INV:{inventory}
Analyze: Who trades fairly? Who hoards? What's scarce? Your best strategy going forward?
Keep under 100 words.
```

**Critical change from v5:** Reflections use the agent's own model family (Llama agents reflect with Llama, Gemini with Gemini, etc.). This preserves behavioral signatures. DeepSeek agents may use reasoner mode for reflection at no extra per-token cost. Reflection frequency increased to every 5 rounds (5 reflections per game vs 3 previously) for richer behavioral trajectory data.

### 2.6 Token Budget (Post-Optimization)

| Component | Input tokens/round | Output tokens/round |
|---|---|---|
| Agent planning (6 × ~90 in, ~40 out) | 540 | 240 |
| Trade proposals (12 × ~60 in, ~35 out) | 720 | 420 |
| Trade responses (12 × ~60 in, ~25 out) | 720 | 300 |
| GM resolution (2 × ~120 in, ~80 out) | 240 | 160 |
| Building decisions (6 × ~70 in, ~30 out) | 420 | 180 |
| Reflection (1.0 avg × ~150 in, ~100 out) | 150 | 100 |
| **Per round** | **~2,790** | **~1,400** |
| **Per game (25 rounds)** | **~69,750** | **~35,000** |

(Reflection increased from 0.72/round to 1.0/round due to every-5-round frequency.)

### 2.7 Optimized Cost Per Game (With Cache Optimization)

| Model | Input cost | Output cost | Total |
|---|---|---|---|
| Llama (Groq, ~35% cached) | $0.031 | $0.027 | **$0.058** |
| DeepSeek V3.2 (chat, ~60% cached) | $0.006 | $0.014 | **$0.020** |
| DeepSeek V3.2 (reasoner, reflection only) | ~$0.001 | ~$0.002 | ~$0.003 extra |
| Gemini Flash (~30% cached) | $0.013 | $0.086 | **$0.099** |
| Mistral Small 3.1 (corrected pricing) | $0.005 | $0.010 | **$0.015** |
| GM (Mistral, ~50 calls) | ~$0.001 | ~$0.002 | **$0.003** |

**Average monoculture game: ~$0.05.** Average pairwise game: ~$0.07.

### 2.8 Total Project Cost

| Phase | Games | Cost |
|---|---|---|
| Phase 0: Pilot + calibration | 30 | $1.50 |
| Phase 1: Monoculture (4 × 30) | 120 | $6.00 |
| Phase 2: Pairwise (6 pairs × 25) | 150 | $10.50 |
| Phase 2B: Persona-vs-Architecture | 20 | $1.00 |
| Phase 2C: Full-mix + Temporal validation | 15 | $1.05 |
| **Subtotal** | **335** | **$20.05** |
| +20% retry/error/debugging overhead | | $4.01 |
| +Buffer for prompt iteration | | $8.00 |
| **TOTAL** | | **~$32 (₹2,700)** |

**Under 55% of one month's budget.** Even if estimates are off by 3×, total is ~$96 — still within the ₹12,500 total budget.

---

## 3. Simulation Design

### Core Mechanics (Updated)

6 agents, 25 rounds, VP-based victory condition (first to 12VP or highest at round 25). Pairwise games use 3v3 configuration with complementary resource specialties.

**Key design fixes:**
- Resource specialty assignments randomized across games and recorded as covariate
- VP values rebalanced: House (W2+S2 → 3VP), Provisions (G2+Wo2 → 3VP), Tools (O2+C2 → 3VP). Equal VP values prevent degenerate strategies where Ore/Clay agents have structural advantage.
- Grain consumption (1G/round) creates scarcity pressure that drives inter-agent dependency

### Concordia v2.0 Integration

Built on Concordia v2.0's Entity-Component architecture:

- **Simultaneous engine** for agent action and trade proposal phases (all 6 agents act in parallel)
- **Sequential resolution** for GM trade validation (prevents double-spending)
- **Per-agent LLM override** (native Concordia v2.0 feature) for pairwise experiments
- **Built-in checkpointing** (save state after each round for crash recovery)
- **Structured JSON logging** (new v2.0 feature) for analysis pipeline
- **Evaluate Concordia's marketplace component** before building custom Trade Island components — may save weeks of development

### JSON Mode Enforcement

All agent and GM calls use provider-native JSON mode. Important provider-specific differences:

- **Groq:** Full `json_schema` enforcement with strict typing. Best reliability.
- **Gemini:** Native `responseJsonSchema` via LiteLLM for Gemini 2.0+. Full schema support. **Critical: disable thinking mode** (`thinking_budget: 0`) on all agent calls to prevent 5-12× output token inflation from hidden reasoning tokens. Enable thinking only for reflection calls if desired.
- **DeepSeek:** Basic `json_object` mode only. Does NOT support `json_schema` enforcement. Include schema in prompt text.
- **Mistral:** Basic `json_object` mode. Include schema in prompt text.

Lightweight tolerant JSON parser retained as fallback for edge cases (<1% expected failure rate with JSON mode).

---

## 4. Experimental Design

| Phase | Games | Calendar Time (at 10-15/day) |
|---|---|---|
| Phase 0: Pilot + calibration + format ablation | 30 | 3-4 days |
| Phase 1: Monoculture (4 × 30) | 120 | 8-10 days |
| Phase 2: Pairwise (6 pairs × 25) | 150 | 10-12 days |
| Phase 2B: Persona-vs-Architecture | 20 | 2 days |
| Phase 2C: Full-mix + temporal validation | 15 | 1-2 days |
| **Total simulation** | **335** | **~25-30 days (4-5 weeks)** |
| Analysis + Writing | — | 4-5 weeks |
| **Total project** | | **~9-10 weeks** |

### Phase 0: Structured Format Ablation (New)

Before running any games, validate prompt format per model:

1. **Format test** (20 calls per model, 4 models = 80 calls, cost ~$0.50): Send identical game states in verbose vs compact format. Measure JSON parse success rate and action quality.
2. **Decision rule:** If compact format produces <90% valid JSON on any model, use verbose for that model only.
3. **GM sensitivity test** (10 games): Run identical scenarios with Mistral GM vs Llama GM to quantify GM confound.

### Pre-Registration (OSF)

H1: Gini coefficient at round 25 differs across 4 families (Kruskal-Wallis, α=0.05)
H2: Cross-model trade acceptance rate depends on pairing identity (logistic mixed-effects, game as random effect)
H3: VP ratio deviates from 1.0 for ≥2 of 6 pairwise conditions (one-sample t-test, BH-corrected)
H4: Architecture variance > persona variance on ≥3 of 5 pre-specified metrics: (1) VP at round 25, (2) trade acceptance rate, (3) Gini coefficient, (4) exploitation index, (5) cooperation tendency score. Tested via permutation-based variance comparison.

**Analysis scripts committed to OSF pre-registration repository as executable stubs before Phase 1 begins.**

---

## 5. Analysis Plan

Key outputs:
- 4×4 pairwise heatmaps (VP ratio, trade acceptance, exploitation index)
- Three-track classifier (behavior/language/meta-behavioral)
- Hierarchical mixed-effects models (game → agent → observation, with resource specialty as covariate)
- BH-corrected pairwise comparisons
- Behavioral drift detection (5-round rolling windows, aligned with reflection frequency)

---

## 6. Technical Stack

```
LiteLLM (provider routing, cost tracking, retry logic, JSON mode, budget cap)
    ↕
Concordia v2.0 (simulation engine)
    ├── Simultaneous Engine (parallel agent actions)
    ├── Per-Agent LLM Override (native v2.0 pairwise support)
    ├── Trade Island Components (evaluate built-in marketplace first)
    ├── Prefix-First Prompt Templates (cache-optimized)
    ├── JSON Mode Enforcement (per-provider native)
    ├── Checkpoint System (per-round state saves)
    └── Structured JSON Lines Logger (v2.0 native)
        ↓
Analysis:
    ├── Polars (fast dataframe processing)
    ├── statsmodels (mixed-effects, Kruskal-Wallis)
    ├── scikit-learn (random forest classifier)
    ├── NetworkX (trade networks)
    ├── sentence-transformers (negotiation embeddings)
    └── seaborn (heatmaps, the paper's signature figures)
```

---

## 7. Limitations

1. Model family ≠ isolated architecture. Combined effect of architecture, training data, RLHF.
2. Small groups (6 agents). Computational experimental economics scale, not macro simulation.
3. Compact prompts may disadvantage models sensitive to abbreviation. Empirically validated in Phase 0 ablation.
4. DeepSeek chat mode (V3.2) used for agent calls. Reasoner mode used for DeepSeek agent reflections only. This may suppress reasoning advantages in action decisions, though per-token cost is now identical.
5. API model instability. All runs timestamped, model versions logged. Mistral pinned to dated version ID. Temporal validation games detect drift.
6. GM confound. Mistral Small GM may advantage Mistral agents. Mitigated by GM-sensitivity test (10 games with Llama GM).
7. Single researcher. All code, data, analysis open-sourced.
8. **4 model families only.** Does not include closed-source models (GPT-4o, Claude). Future work can extend.
9. **DeepSeek data sovereignty.** Data transmitted to Chinese servers. All transmitted data is synthetic game states, not personally identifiable.

---

## 8. Related Work (New Section)

This study builds on and differentiates from:

- **CompeteAI** (Zhao et al., 2023): Studies competition dynamics in LLM agents but uses single-model setup. We extend to systematic all-pairs cross-model comparison.
- **Alympics** (Mao et al., 2023): LLM agents in game-theoretic settings. Focuses on single games (prisoner's dilemma, auctions), not extended multi-round economic simulation with trade.
- **Magentic Marketplace** (Microsoft Research, 2025): Open-source agentic market environment. More sophisticated market design but does not study model family differences.
- **Concordia** (Vezhnevets et al., 2023; v2.0 2025): Our simulation engine. The framework for GABMs, which we instantiate with a specific economic domain.
- **LLM-MAS Surveys** (Nature 2024, IJCAI 2024): Establish taxonomy of multi-agent LLM systems. We contribute empirical data to the cooperation/competition dimension they identify as underexplored.

**Our unique contribution:** Systematic pairwise comparison across model families under controlled conditions, with the persona-vs-architecture experiment providing causal evidence for the role of model identity.

---

## 9. Budget Summary

| Item | Cost (₹) | Cost ($) |
|---|---|---|
| Total API costs (335 games + overhead) | ~₹2,700 | ~$32 |
| LiteLLM infrastructure | ₹0 | $0 (open source) |
| Concordia v2.0 | ₹0 | $0 (open source) |
| Compute (local laptop) | ₹0 | $0 |
| **Total project cost** | **~₹2,700** | **~$32** |
| Budget available (₹5,000/mo × 2.5 months) | ₹12,500 | $148 |
| **Remaining budget** | **₹9,800** | **$116** |

Remaining budget covers: reruns, additional experiments for revisions, potential 5th model family addition, conference registration.

---

## 10. Timeline

| Week | Activity |
|---|---|
| 1 | LiteLLM + Concordia v2.0 integration, evaluate marketplace component, compact prompt templates, JSON mode setup |
| 2 | Phase 0: Format ablation, prompt calibration, GM sensitivity tests (30 games) |
| 3-4 | Phase 1: 120 monoculture games (30 per model, ~15/day) |
| 5-7 | Phase 2: 150 pairwise games + 20 persona games (~12/day) |
| 8 | Phase 2C: 15 validation games. Begin analysis. |
| 9-10 | Full statistical analysis, heatmap generation, classifier training |
| 11 | Paper writing, figures (target: NeurIPS workshop short version) |
| 12 | Revision, code cleanup, data release prep, arXiv preprint |
| 13+ | Submit AAMAS 2027 full paper, blog post |

---

## 11. Deliverables

1. **Paper** — NeurIPS 2026 Workshop + AAMAS 2027 full paper + arXiv preprint
2. **concordia-pairwise** — Open-source library: LiteLLM + Concordia v2.0 for multi-model economic simulation (all dependencies version-pinned)
3. **model-pairwise-benchmark** — One-command tool: `python benchmark.py --model-a llama-70b --model-b deepseek-chat --games 25`
4. **trade-island-dataset** — Full logs from 335+ games (Hugging Face Datasets)
5. **analysis-notebooks** — Reproducible Jupyter notebooks with pre-registered analysis scripts
6. **Blog/Content** — Narrative highlights, pairwise heatmap graphics, findings thread

---

*This blueprint has undergone 5 rounds of multi-role audit (44+ expert perspectives, 120+ issues identified and addressed). Verified against official API pricing as of March 15, 2026. The all-paid, cache-optimized design costs ~₹2,700 total, runs in 5 weeks of simulation, and produces 335 games of clean data — a 37% cost reduction and 17% more games versus v5.*
