"""Validate this pass independently of concurrent edits to other map assets.

audit.py remains the strict historical check against the original source hash
snapshot. This check does not replace its baseline or claim unchanged dressing.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_finish as Q
import lowtide_map as L
import lowtide_marine as M
import lowtide_masonry as S
import lowtide_static as STATIC

folder = Path(__file__).parent
old = json.loads((folder / "before/Assets/scenes/maps/Lowtide/lowtide.scene").read_text())
new = json.loads(L.SCENE_FILE.read_text())
old_roots = {o.get("Name", o["__guid"]): o for o in old["GameObjects"]}
new_roots = {o.get("Name", o["__guid"]): o for o in new["GameObjects"]}
assert old["SceneProperties"] == new["SceneProperties"]
for name, obj in old_roots.items():
    if name not in {"Sun", "Fog", "Look", "Lowtide", "Reflection Probes", "Lights"}:
        assert new_roots[name] == obj, name
lighting_original = json.loads((folder / "warehouse-lighting-before/lowtide.scene").read_text())
lighting_root = next(o for o in lighting_original["GameObjects"] if o.get("Name") == "Lights")
assert lighting_root == old_roots["Lights"]
# The dedicated lighting scope check validates all changes within this root.
children = copy.deepcopy(new_roots["Lowtide"]["Children"])
for child in children:
    if child.get("Name") in STATIC.WORLD_MESHES:
        child["Flags"] &= ~STATIC.STATIC
for name, stem in (("Harbour Details", "finish"), ("Tidal Details", "marine"), ("Masonry Details", "masonry")):
    objects = [o for o in children if o["Name"] == name]
    assert len(objects) == 1
    assert [c["__type"] for c in objects[0]["Components"]] == ["Sandbox.ModelRenderer"]
    assert "Physics" not in (L.OUT_DIR / f"lowtide_{stem}.vmdl").read_text()
    children.remove(objects[0])
water = next(o for o in children if o["Name"] == "Water")
reflections = [c for c in water["Components"] if c["__type"] == "Facepunch.LowtideWaterReflections"]
assert len(reflections) == 1 and reflections[0]["WaterHeight"] == -137
water["Components"].remove(reflections[0])
assert children == old_roots["Lowtide"]["Children"]
stable = json.dumps(new, sort_keys=True)
Q.apply_scene(new, L)
M.apply_scene(new, L)
S.apply_scene(new, L)
assert json.dumps(new, sort_keys=True) == stable
for side in ("east", "west"):
    name = f"lowtide_{side}.vmdl"
    before_roof = (folder / "roof-before" / name).read_text()
    before_interior = (folder / "interior-before" / name).read_text()
    before_ceiling = (folder / "ceiling-before" / name).read_text()
    current = (L.OUT_DIR / name).read_text()
    before_windows = (folder / "window-before" / name).read_text()
    assert current.replace("materials/lowtide/windows/lt_window_interior.vmat", "materials/railhead/rw_window_dark.vmat") == before_windows
    assert before_windows.replace("materials/lowtide/interior/lt_ceiling.vmat", "materials/buildings/planks_dark.vmat") == before_ceiling
    assert before_ceiling.replace("materials/lowtide/interior/lt_concrete.vmat", "materials/railhead/rw_concrete.vmat") == before_interior
    assert before_interior.replace("materials/lowtide/roofs/lt_slate.vmat", "materials/buildings/slate.vmat") == before_roof
assert (L.OUT_DIR / "lowtide_glass.vmdl").read_text().replace(
    "materials/lowtide/lt_glass.vmat", "materials/railhead/rw_glass.vmat") == (folder / "glass-before.vmdl").read_text()
lines = [
    "PASS: original gameplay roots, spawns, objectives and navigation settings retained",
    "PASS: original Lights baseline retained; warehouse-lighting-checks.py validates its scoped update",
    "PASS: original renderer/collider scene declarations retained except canal reflections and reviewed static flags",
    "PASS: three visual detail meshes each have exactly one renderer and no physics declarations",
    "PASS: scoped scene patches are idempotent, including preservation of concurrent root additions",
    "PASS: roof remap changes only the slate material path; model geometry and collision descriptions retained",
    "PASS: concrete remap changes only its material path relative to the pre-interior snapshot",
    "PASS: ceiling remap changes only its material path relative to the pre-ceiling snapshot",
    "PASS: sealed-window architecture remap changes only its material path; separate window-scope-checks.py verifies all OBJ edits are restricted to sealed-window UVs",
    "PASS: glazing remap changes only its material path; glass collision descriptions retained",
    "LIMITATION: strict audit.py baseline predates concurrent dressing edits and this pass's architectural UVs; this report makes no claim about dressing geometry",
]
(folder / "current-scope-checks.txt").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
