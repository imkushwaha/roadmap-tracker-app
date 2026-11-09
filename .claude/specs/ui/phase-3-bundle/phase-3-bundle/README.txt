Phase 3 bundle (optional convenience; the spec is self-contained without it)
REQUIRES Phases 0, 1 and 2 to be applied first. Phase 3 adds NO new files: everything is applied by scripts.

scripts/   Run from the REPO ROOT, in this order:
             python3 step3_misc.py && python3 step3_appjs.py && python3 step3_docs.py
           Then, once, against your copy of verify_phase2.py (kept outside the repo):
             python3 patch_phase2_harness.py /path/to/verify_phase2.py
           Do not commit the scripts.
verify/    Keep OUTSIDE the repo (next to Phase 0's serve-demo.js). See section 7 of PHASE_3_HOME_FLOWS_SPEC.md.
Expected: npm test = 79/79; verify_phase3.py = RESULT 88/88; regressions: verify_phase2.py (patched) 114/114,
          verify_phase1.py 67/67, verify_phase0.py 61/61.
