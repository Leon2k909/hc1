"""Point the yard floor at the v2 concrete (install) or back at the original (revert).

    python install.py            the yard model's floor uses materials/boxyard/yard_concrete_v2/bx_yard_concrete.vmat
    python install.py revert     back to materials/boxyard/bx_concrete.vmat

Only the material remap line in boxyard_yard.vmdl changes.  The old material and its textures are untouched (the
backdrop outside the wall still uses them)."""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
VMDL = os.path.join(ROOT, "Assets", "models", "maps", "boxyard", "boxyard_yard.vmdl")
OLD = '{ from = "bx_concrete.vmat" to = "materials/boxyard/bx_concrete.vmat" }'
NEW = '{ from = "bx_concrete.vmat" to = "materials/boxyard/yard_concrete_v2/bx_yard_concrete.vmat" }'

revert = len(sys.argv) > 1 and sys.argv[1] == "revert"
src, dst = (NEW, OLD) if revert else (OLD, NEW)
with open(VMDL, encoding="utf-8", newline="") as fh:
    text = fh.read()
if dst in text:
    print("already", "reverted" if revert else "installed")
elif src not in text:
    sys.exit("remap line not found in " + VMDL)
else:
    with open(VMDL, "w", encoding="utf-8", newline="") as fh:
        fh.write(text.replace(src, dst))
    print("reverted" if revert else "installed")
