Phase 2 bundle (optional convenience; the spec is self-contained without it)
REQUIRES Phases 0 and 1 to be applied first.

new-files/   Copy into the repo root, keeping folder names (css/, js/, server/roadmaps/, test/).
scripts/     Run from the REPO ROOT, in this order:
               python3 step2_server.py && python3 step2_misc.py && python3 step2_styles.py \
               && python3 step2_index.py && python3 step2_appjs.py && python3 step2_docs.py
             Do not commit the scripts.
verify/      Keep OUTSIDE the repo (next to Phase 0's serve-demo.js). See section 7 of PHASE_2_SHELL_AND_HOME_SPEC.md.
Expected: npm test = 79/79; verify_phase2.py = RESULT 114/114; regressions: verify_phase1.py 67/67, verify_phase0.py 61/61.
