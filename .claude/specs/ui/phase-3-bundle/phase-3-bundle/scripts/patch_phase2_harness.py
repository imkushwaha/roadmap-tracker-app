"""Phase 3 / keep the Phase 2 harness runnable.
Phase 3 requires typing a roadmap's name before deleting one that has progress, so the Phase 2 harness must
type it too. Run once, next to verify_phase2.py:  python3 patch_phase2_harness.py /tmp/ui-verify/verify_phase2.py"""
import sys

path = sys.argv[1]
s = open(path, encoding="utf-8").read()
assert "def confirm_delete" not in s, "already patched"

HELPER = '''def confirm_delete(page):
    """Phase 3: roadmaps with progress need their name typed before Delete is enabled."""
    field = page.locator("#deleteConfirmName")
    if field.count():
        field.fill(field.get_attribute("data-name"))
    page.click("[data-action=confirm-delete-roadmap]")


'''
marker = "def home(page):"
assert s.count(marker) == 1
s = s.replace(marker, HELPER + marker)

old = 'page.click("[data-action=confirm-delete-roadmap]")'
n = s.count(old) - 1          # the helper itself contains one occurrence
assert n >= 3, f"expected at least 3 delete confirmations to patch, found {n}"
head, tail = s.split(HELPER, 1)
tail_head, rest = tail.split("def home(page):", 1)
rest = rest.replace(old, "confirm_delete(page)")
s = head + HELPER + tail_head + "def home(page):" + rest
open(path, "w", encoding="utf-8").write(s)
print(f"patched {n} delete confirmations in {path}")
