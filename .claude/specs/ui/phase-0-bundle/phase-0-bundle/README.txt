Phase 0 bundle (optional convenience; the spec is self-contained without it)

new-files/   Copy into the repo root, keeping folder names (css/, js/, img/, fonts/, documentation/).
scripts/     Run from the REPO ROOT, in this order:
               python3 step_styles.py && python3 step_index.py && python3 step_appjs.py \
               && python3 step_server.py && python3 step_docs.py
             Do not commit the scripts.
verify/      Keep OUTSIDE the repo. See section 7 of PHASE_0_FOUNDATIONS_SPEC.md.
Expected result: npm test = 59/59; harness = RESULT 61/61.
