"""Temporary focused regeneration/verification for Lowtide's Fleet lanterns."""
import hashlib
from collections import Counter
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))

import lowtide_map as M
import map_kit as K

STAGE = Path(__file__).parent / "stage"
CANON = ROOT / "Assets/models/maps/lowtide"
STAGE.mkdir(exist_ok=True)

model = M.fleet()
M.MARINE.strip_model(model)
M.configure(model)
count = K.write_model(STAGE, "models/maps/lowtide", "lowtide_fleet", model)
print("Fleet triangles:", count, "hulls:", len(model.hulls), "boxes:", len(model.boxes))
for path in sorted(STAGE.glob("lowtide_fleet*")):
    expected = CANON / path.name
    new_digest = hashlib.sha256(path.read_bytes()).hexdigest()
    old_digest = hashlib.sha256(expected.read_bytes()).hexdigest() if expected.exists() else "missing"
    print(path.name, "same=" + str(new_digest == old_digest), "new=" + new_digest[:12], "old=" + old_digest[:12])
print("placements:", M.LANTERNS.placements())

def surfaces(path):
    vertices = [None]
    triangles = Counter()
    paints = Counter()
    paint = None
    for line in path.open(encoding="utf-8"):
        if line.startswith("v "):
            vertices.append(tuple(line.split()[1:4]))
        elif line.startswith("usemtl "):
            paint = line.split()[1]
        elif line.startswith("f "):
            pts = tuple(sorted(vertices[int(ref.partition("/")[0])] for ref in line.split()[1:]))
            triangles[(paint, pts)] += 1
            paints[paint] += 1
    return triangles, paints

before, before_paints = surfaces(CANON / "lowtide_fleet.obj")
after, after_paints = surfaces(STAGE / "lowtide_fleet.obj")
print("existing triangle count", sum(before_paints.values()))
print("staged triangle count", sum(after_paints.values()))
print("missing triangles", sum((before - after).values()))
print("new triangles", sum((after - before).values()))
print("changed paint counts", [(p, before_paints[p], after_paints[p]) for p in (before_paints.keys() | after_paints.keys()) if before_paints[p] != after_paints[p]])
removed, added = before - after, after - before
print("removed materials", dict(Counter({p:sum(qty for (paint, _), qty in removed.items() if paint == p) for p, _ in removed})))
print("added materials", dict(Counter({p:sum(qty for (paint, _), qty in added.items() if paint == p) for p, _ in added})))
affected = {p for p, _ in removed} | {p for p, _ in added}
expected = {"iron_green", "lt_lantern_iron", "lt_lantern_glass", "lt_lantern_bulb", "lt_lantern_brass"}
assert affected <= expected, f"Unrelated geometry moved: {affected - expected}"
assert sum(before_paints.values()) == sum(after_paints.values())
assert {p for p in before_paints} == {p for p in after_paints}
assert len(model.boxes) == 25 and len(model.hulls) == 22
assert [(e,n) for e,n,_ in M.LANTERNS.placements()] == [(-240,1167),(-240,1433),(240,1167),(240,1433)]
roof_edge = 10.15
assert min(1167 - roof_edge - M.STREET_N[0], M.STREET_N[1] - 1433 - roof_edge) > 6
print("PASS: identical triangle counts/materials; movements scoped to bridge lighting; roof-wall clearance > 6 inches")
