# Archived Analysis Stubs

These stubs were written for the original Trade Island / Harbour primary-study design
and are **superseded** by the CFIM/RNE redesign (SIMULATION_DESIGN.md).

They are retained here per D056 ("retained in repo history but superseded") so that
the git audit trail is intact. Do not import or reference these files from new code.

| File | Original hypothesis | Superseded by |
|------|---------------------|---------------|
| `h1_kruskal_wallis.py` | H1: Gini coefficient differs across 4 families (Kruskal-Wallis) | `h1_self_play_premium.py` |
| `h2_logistic_mixed_effects.py` | H2: Trade acceptance logistic model | `h2_mixed_effects.py` |
| `h3_vp_ratio_ttest.py` | H3: VP ratio t-test | `h3_identity_disclosure.py` |
| `h4_architecture_vs_persona.py` | H4: Architecture vs. persona | `h4_adaptation_lag.py` |

The replacement stubs (`h1_self_play_premium.py` through `h5_cfim_to_multiagent.py`)
are in `src/analysis/` and are pre-registered for the CFIM study (D056, D057).
