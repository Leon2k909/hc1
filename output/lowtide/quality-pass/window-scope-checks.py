"""Verify the sealed-window patch against the preserved pre-patch assets."""
import hashlib
import json
from pathlib import Path
import re
import sys

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_windows as W

manifest = json.loads((FOLDER / "window-stage/manifest.json").read_text())
results = {}
for name in W.NAMES:
    before = FOLDER / "window-before" / (name + ".obj")
    after = W.K.ASSETS / "models/maps/lowtide" / (name + ".obj")
    assert hashlib.sha256(before.read_bytes()).hexdigest() == manifest[name]["sha256"]
    expected, counts = W.prepare_obj(before)
    actual = after.read_bytes()
    assert expected == actual, f"Unexpected geometry or non-window UV edit: {name}"
    assert W.prepare_obj(after)[0] == actual, f"Non-idempotent window UVs: {name}"
    # Compare every geometry, normal, face and material record independently.
    records = lambda data: [line for line in data.splitlines() if not line.startswith(b"vt ")]
    assert records(before.read_bytes()) == records(actual)
    old_model = before.with_suffix(".vmdl").read_text()
    new_model = after.with_suffix(".vmdl").read_text()
    assert new_model == old_model.replace("materials/railhead/rw_window_dark.vmat", W.MATERIAL)
    results[name] = {
        "windows": counts["windows"], "uv_count": counts["uv_count"],
        "geometry_unchanged": True, "collision_unchanged": True,
        "non_window_uvs_unchanged": True, "idempotent": True,
    }

compiled = (W.K.ASSETS / W.MATERIAL).with_suffix(".vmat_c")
refs = sorted(set(x.decode() for x in re.findall(rb"materials/[a-zA-Z0-9_./-]+[.]vtex", compiled.read_bytes())))
assert refs, "Compiled material texture references were not found"
dependencies = {ref: (W.K.ASSETS / (ref + "_c")).exists() for ref in refs}
# The material deliberately uses compiled, project-local textures so missing
# generated engine defaults cannot silently produce the previous checkerboard.
assert all(dependencies.values()), dependencies
results["texture_dependencies"] = dependencies
(FOLDER / "window-scope-checks.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
