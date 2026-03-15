# S07: OSF Pre-Registration

**Authoritative spec:** `.gsd/milestones/M001/slices/S05/S05-PLAN.md`
**Note:** This slice was dispatched as S07. The canonical slice plan content is in S05-PLAN.md.

**Goal:** Submit formal OSF pre-registration before any Phase 1 production games begin. Lock hypotheses H1–H5 with analysis stubs committed. Record registration URL.
**Demo:** OSF registration URL recorded in `data/metadata/osf_registration.json`. `docs/osf_preregistration.md` committed. Analysis stubs H1–H5 committed and referenced by the registration.

## Must-Haves

- `docs/osf_preregistration.md` — complete pre-registration document with exact statistical statements for H1–H5
- `data/metadata/osf_registration.json` — with OSF URLs (pending human submission for T02)
- Analysis stubs `src/analysis/h1_*` through `src/analysis/h5_*` committed before registration submission
- `metrics.json` updated with `hypotheses_preregistered: true`

## CRITICAL CONSTRAINT

This slice must complete before any Phase 1 production games begin.

## Verification

```bash
cat data/metadata/osf_registration.json
python -c "
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
- [ ] **T02: Create OSF project and submit formal registration** `est:1h`
  - Human action required — see S05-PLAN.md T02 for exact steps.
