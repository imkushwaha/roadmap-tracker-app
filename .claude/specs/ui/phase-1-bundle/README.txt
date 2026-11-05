Phase 1 bundle (optional convenience; the spec is self-contained without it)
REQUIRES Phase 0 to be applied first.

new-files/   Copy into the repo root, keeping folder names (css/, js/).
scripts/     Run from the REPO ROOT, in this order:
               python3 step1_components.py && python3 step1_styles.py && python3 step1_index.py \
               && python3 step1_appjs.py && python3 step1_docs.py
             Do not commit the scripts.
verify/      Keep OUTSIDE the repo (next to Phase 0's serve-demo.js). See section 7 of PHASE_1_AUTH_SCREENS_SPEC.md.
Expected: npm test = 59/59; verify_phase1.py = RESULT 67/67; verify_phase0.py (regression) = RESULT 61/61.
