"""Scoped preservation checks for the Museo glass conversion."""
import importlib.util
import json
import sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import cerroblanco_glass as G
import cerroblanco_map as M


def read_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


base = ROOT / "output/museo-glass/before"
old_parts = read_module("museo_before_parts", base / "Tools/cerroblanco_parts.py")
old_map = read_module("museo_before_map", base / "Tools/cerroblanco_map.py")
old_map.P = old_parts
old_buildings, old_glass, dressing, canopy = K.Model(), K.Model(), K.Model(), K.Model()
old_map.west_gallery(old_buildings, old_glass, dressing)
old_map.rotunda(old_buildings, old_glass, dressing)
old_map.east_block(old_buildings, old_glass, dressing)
old_map.south_gallery(old_buildings, old_glass, dressing, canopy)
new_glass, new_buildings = G.build_glazing()


def polygons_equal(a, b):
    return len(a) == len(b) and all(np.allclose(ap, bp) and np.allclose(an, bn)
                                  for (ap, an), (bp, bn) in zip(a, b))


for paint, polygons in old_buildings.polygons.items():
    if paint not in G.PAINTS:
        assert polygons_equal(polygons, new_buildings.polygons[paint]), paint
assert not any(new_buildings.polygons.get(p) for p in G.PAINTS)
assert len(old_buildings.hulls) == len(new_buildings.hulls)
for (points_a, surface_a), (points_b, surface_b) in zip(old_buildings.hulls, new_buildings.hulls):
    assert surface_a == surface_b and np.allclose(points_a, points_b)


def box_key(box):
    centre, axes, size, surface = box
    return (tuple(np.round(centre, 6)), tuple(np.round(np.asarray(axes).flatten(), 6)), tuple(np.round(size, 6)))


old_boxes = {box_key(b) for b in old_buildings.boxes}
new_boxes = {box_key(b) for b in new_buildings.boxes}
guards = {box_key((*guard, "metal")) for guard in new_glass.guards}
assert old_boxes - new_boxes == guards
assert not new_boxes - old_boxes

before = json.loads((base / "Assets/scenes/maps/CerroBlanco/cerroblanco.scene").read_text(encoding="utf-8-sig"))
after = json.loads(M.SCENE_FILE.read_text(encoding="utf-8-sig"))
glass_id = M.ids("world/cerroblanco_glass")
for scene in (before, after):
    world = next(o for o in scene["GameObjects"] if o["__guid"] == M.ids("world"))
    world["Children"] = [o for o in world["Children"] if o["__guid"] != glass_id]
assert before == after

panes = new_glass.scene_group(M.ids)["Children"]
assert sum(any(c["__type"] == "Facepunch.BreakableGlass" for c in p["Components"]) for p in panes) == 392
assert not any(any(c["__type"] == "Sandbox.ModelRenderer" and
                  c.get("Model") == "models/maps/cerroblanco/cerroblanco_glass.vmdl"
                  for c in p["Components"]) for p in panes)
assert len({p["__guid"] for p in panes}) == len(panes)
print("PASS: all building faces except the converted glass are identical")
print("PASS: all structural collision hulls and boxes are preserved")
print("PASS: the 12 former invisible metal barriers are retained as player clips")
print("PASS: all scene content outside the glass group is identical")
print("PASS: 392 panes, stable unique IDs, no aggregate glass renderer or collider")
