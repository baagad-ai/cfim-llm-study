---
estimated_steps: 5
estimated_files: 2
---

> **RENAMED (2026-03-15 audit):** This task is now T06 in the restructured S04. Two tasks were inserted before it: T03-FIX (repair sprint) and T04-VALIDATION (5-game validation). The file T04-PLAN.md filename remains as-is for continuity but this task is executed as T06.
>
> **Updated scope:** GM confound section must use ≥10 Llama-GM games (upgraded from 5). DECISIONS.md should now include D045–D050 range (repair sprint decisions). Add Go/No-Go gate language referencing validated VP range and acceptance rate from T04-VALIDATION.

# T06 (was T04): Write Phase 0 report and update DECISIONS.md

**Slice:** S04 — Phase 0 Calibration (30 games)
**Milestone:** M001

## Description

Synthesizes all S04 findings into `data/phase0/PHASE0_REPORT.md` — a human-readable document that allows a reviewer to make the Go/No-Go decision for Phase 1 without reading raw JSONL. The report is the slice's final artifact and the Phase 1 gate.

Also closes open DECISIONS.md entries: D037 resolution (trade acceptance), D041–D044 format locks (if not already written in T02), D045 for the `inventory_value` docstring discrepancy.

## Steps

1. **Extract metrics from JSONL** using `jq` and Python:
   ```bash
   # Total cost (phase0 games only)
   jq -r 'select(.event=="game_end" and .config_name=="phase0") | .total_cost_usd' \
     data/raw/*/game.jsonl | python3 -c "import sys; v=[float(l) for l in sys.stdin]; \
     print(f'Total: ${sum(v):.4f}, Avg: ${sum(v)/len(v):.4f}, N={len(v)}')"

   # Trade acceptance rate
   total_proposals=$(grep -c '"action_type": "trade"' data/raw/*/game.jsonl || echo 0)
   total_accepted=$(grep -c '"accepted": true' data/raw/*/game.jsonl || echo 0)
   echo "Proposals: $total_proposals, Accepted: $total_accepted"

   # VP distribution by model family (round 25 only)
   python3 -c "
   import json, glob, collections, statistics
   vp_by_family = collections.defaultdict(list)
   for f in glob.glob('data/raw/*/game.jsonl'):
       for line in open(f):
           d = json.loads(line)
           if d.get('event') == 'round_end' and d.get('round') == 25:
               vp_by_family[d['model_family']].append(d['vp'])
   for fam, vps in sorted(vp_by_family.items()):
       print(f'{fam}: n={len(vps)} mean={statistics.mean(vps):.1f} std={statistics.stdev(vps) if len(vps)>1 else 0:.1f}')
   "

   # GM parse failure count
   grep -c gm_parse_failure data/raw/*/game.jsonl 2>/dev/null | grep -v ':0$' | wc -l

   # GM confound: avg final VP in Mistral-GM vs Llama-GM games
   # (requires knowing which game IDs are sensitivity games)
   ```

2. **Compute GM confound** — compare mean final VP across Mistral-GM games (default phase0) vs Llama-GM sensitivity games. Extract from `round_end` events at `round == 25`. If delta is < 2 VP points, confound is negligible. If ≥ 2 VP points with consistent direction, note it as a limitation for Phase 1 analysis.

3. **Write `data/phase0/PHASE0_REPORT.md`** with exactly these 5 sections:

   **Section 1 — Format Decision Per Model** (from T02 ablation results)
   - Table: model family | compact parse rate | verbose parse rate | decision
   - Confirm all 4 families have a locked format

   **Section 2 — Trade Acceptance Rate**
   - Total proposals generated, total accepted, acceptance rate %
   - D037 resolution: if ≥1 accepted, declare resolved; if still 0, escalate with recommended next step (explicit VP gain injection in user message)
   - Note first game where acceptance occurred (game_id)

   **Section 3 — GM Confound Quantification**
   - Mean final VP: Mistral-GM games vs Llama-GM games (with n per group)
   - Delta and direction; conclusion: negligible / material / unknown
   - Recommendation: proceed with Mistral GM for Phase 1 or switch (per D008 revisable note)

   **Section 4 — Cost Breakdown**
   - Total cost, per-game average, per-family breakdown
   - Budget: actual vs $1.50 cap; headroom
   - Note on Mistral cost tracking (was previously 0.0 in S02; now fixed per T01)

   **Section 5 — Go/No-Go Decision for Phase 1**
   - State the decision explicitly: **GO** or **NO-GO**
   - Required conditions for GO: all 4 providers working, ≥1 accepted trade, total cost ≤$1.50, no systematic parse failure on any model
   - If NO-GO: list specific blocking issues with remediation steps before reopening Phase 1

4. **Append to `.gsd/DECISIONS.md`**:
   - D045: `inventory_value` absent from `round_end` events; present only in H1 stub docstring (not actual test code); schema frozen — do not add this field (would silently break pre-registered analysis if field changed the df shape unexpectedly). Note: docstring comment is aspirational and misleading; fix it when editing `h1_kruskal_wallis.py` during M004 analysis work.
   - D037 update row: resolved if ≥1 accepted trade; escalated if still 0 (with evidence of proposal count)
   - D041–D044: if not already written in T02, add them now with ablation parse rates

5. **Final slice verification pass** — run all verification commands from `S04-PLAN.md` verification block and confirm all pass before marking S04 complete.

## Must-Haves

- [ ] `data/phase0/PHASE0_REPORT.md` exists with all 5 sections populated with real numbers (not placeholders)
- [ ] Section 5 contains an explicit **GO** or **NO-GO** decision
- [ ] D037 row updated in DECISIONS.md (resolved or escalated with evidence)
- [ ] D045 appended to DECISIONS.md
- [ ] D041–D044 present in DECISIONS.md (from T02 or added here if T02 didn't append them)

## Verification

```bash
# Report exists
test -f data/phase0/PHASE0_REPORT.md && echo "report: ok"

# All 5 sections present
for section in "Format Decision" "Trade Acceptance" "GM Confound" "Cost Breakdown" "Go/No-Go"; do
  grep -qi "$section" data/phase0/PHASE0_REPORT.md && echo "✓ $section" || echo "✗ MISSING: $section"
done

# Go/No-Go decision present
grep -iE "(## |GO|NO-GO)" data/phase0/PHASE0_REPORT.md | grep -iE "go"

# DECISIONS.md entries
grep "D04[1-5]" .gsd/DECISIONS.md | wc -l
# → ≥ 5

grep "D037" .gsd/DECISIONS.md | wc -l
# → ≥ 2 (original + update row)
```

## Inputs

- T03 complete: 30 calibration game JSONL files in `data/raw/`; 5 Llama-GM sensitivity game IDs known
- T02 complete: ablation output with per-model parse rates; D041–D044 in DECISIONS.md (or notes from ablation_output.txt)
- `.gsd/DECISIONS.md` — append-only; D037 original row already present for reference

## Expected Output

- `data/phase0/PHASE0_REPORT.md` — 5-section report with real data; Go/No-Go decision
- `.gsd/DECISIONS.md` — D037 update + D045 appended; D041–D044 confirmed present
