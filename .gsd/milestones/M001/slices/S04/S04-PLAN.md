# S04: OSF Pre-Registration

**Goal:** Submit formal OSF pre-registration before any Phase 1 production games begin. Lock hypotheses H1–H5 with analysis stubs committed. Record registration URL.
**Demo:** OSF registration URL recorded in `data/metadata/osf_registration.json`. `docs/osf_preregistration.md` committed. Analysis stubs H1–H5 committed and referenced by the registration.

## CRITICAL CONSTRAINT

This slice must complete before any Phase 1 production games begin.

## Must-Haves

- `docs/osf_preregistration.md` — complete pre-registration document with exact statistical statements for H1–H5
- `data/metadata/osf_registration.json` — with OSF URLs (pending human submission for T02)
- Analysis stubs `src/analysis/h1_*` through `src/analysis/h5_*` committed before registration submission
- `metrics.json` updated with `hypotheses_preregistered: true`

## Proof Level

- Human action required — T02 requires human OSF account creation and form submission

## Verification

```bash
cat data/metadata/osf_registration.json
python3 -c "
import json, pathlib
d = json.loads(pathlib.Path('data/metadata/osf_registration.json').read_text())
assert d.get('osf_registration_url'), 'no registration URL'
assert d.get('registered_at'), 'no timestamp'
print('OSF registration confirmed:', d['osf_registration_url'])
"
git log --oneline src/analysis/
```

## Tasks

- [x] **T01: Write pre-registration document and analysis stubs** `est:2h`
  > DONE. `docs/osf_preregistration.md` written (2934 words). Analysis stubs H1–H5 written for CFIM/RNE design (D056). Old Harbour stubs superseded. `data/metadata/osf_registration.json` placeholder written. `metrics.json` updated.

- [x] **T02: Create OSF project and submit formal registration** `est:1h`
  > **Human action required.** Go to osf.io → create account → new project titled 'Cross-Family Interaction Matrix: Opponent-Contingent Behavioral Profiles in LLM Agents' → set visibility to public → upload `docs/osf_preregistration.md` → Registrations tab → New registration → Open-Ended Registration → link GitHub repo → Submit. Then update `data/metadata/osf_registration.json` with URL and timestamp.

- [ ] **T03: Record URL + commit** `est:10m`
  > Update `data/metadata/osf_registration.json` with real registration URL and timestamp after T02 human step. Commit.

## Files Likely Touched

- `data/metadata/osf_registration.json` — update with real URL after T02
- `.gsd/STATE.md` — update after T02/T03 complete
