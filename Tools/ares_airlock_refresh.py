"""Replace only Ares' three old airlock render assemblies, retaining the hall's other geometry and collision.

Stage with --out. Reproduce after installation with --source-root output/ares/airlocks-20261020/before.
Import the OBJ, MTL and material-only ModelDoc update through Sources/Ares/airlocks/import.cs.txt.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re

import numpy as np

import ares_map as A
from ares_airlock import pressure_door
from ares_screen_refresh import Obj
import map_kit as K

ROOT = Path(__file__).resolve().parent.parent
RELATIVE = Path("Assets/models/maps/ares/ares_hall.obj")


def stage(out, source_root):
    original = source_root / RELATIVE
    model = Obj(original)
    replacement = K.Model()
    door_reports = []
    removed = set()
    for side in (-1, 1):
        face = side * (A.WING_E - .5)
        corner_a, corner_b = np.array((face, -166, 0)), np.array((face - side * 12, 46, 196))
        low, high = np.minimum(corner_a, corner_b), np.maximum(corner_a, corner_b)
        bounds = (low, high)
        door_reports.append((f"wing-{side}", bounds, (face, -60, 0), (-side, 0), 180, 180, 16))
    door_reports.append(("cargo", (np.array((-180, -1400, 0)), np.array((180, -1387.5, 220))),
                         (0, A.CON_N0 + .5, 0), (0, 1), 320, 200, 20))
    summary = []
    for name, (low, high), centre, facing, width, height, border in door_reports:
        selected = set()
        for face in model.faces:
            points = np.array([model.values["v"][p[0]] for p in face["points"]])
            plan = np.c_[-points[:, 0], points[:, 2], points[:, 1]]
            if np.all(plan >= low - .001) and np.all(plan <= high + .001):
                if face["material"] not in ("ar_hazard", "ar_gunmetal", "ar_dark", "ar_steel"):
                    raise ValueError("Unexpected material inside old hatch bounds")
                selected.add(face["line"])
        if len(selected) != 72:
            raise ValueError(f"Expected the original six boxes in {name}, got {len(selected)} triangles")
        removed.update(selected)
        first = {paint: len(items) for paint, items in replacement.polygons.items()}
        pressure_door(replacement, centre, facing, width, height, border)
        # Every newly added point must stay in the original collision envelope.
        points = np.array([p for paint, polys in replacement.polygons.items()
                           for polygon, _ in polys[first.get(paint, 0):] for p in polygon])
        if np.any(points < low - .002) or np.any(points > high + .002):
            raise ValueError(f"New pressure door exceeds the old envelope: {name}")
        summary.append({"door": name, "old_triangles": len(selected), "bounds_low": low.tolist(), "bounds_high": high.tolist()})
    if replacement.boxes or replacement.hulls:
        raise ValueError("The pressure-door detail must not change collision")
    A.configure(replacement)
    fragment_dir = out.parent / "fragment"
    fragment_dir.mkdir(parents=True, exist_ok=True)
    fragment_file = fragment_dir / "airlocks.obj"
    added = K.write_obj(fragment_file, replacement, "ares_hall")
    fragment = Obj(fragment_file)
    offsets = {kind: len(model.values[kind]) - 1 for kind in ("v", "vt", "vn")}
    # Leave every previous attribute/index intact; append only the replacement hatch attributes and triangles.
    for line in removed:
        model.lines[line] = ""
    for line in fragment.lines:
        if line.split(maxsplit=1)[0:1] in (["v"], ["vt"], ["vn"]):
            model.lines.append(line)
    model.lines.append("g pressure_airlocks\n")
    paint = None
    for face in fragment.faces:
        if face["material"] != paint:
            paint = face["material"]
            model.lines.append(f"usemtl {paint}\n")
        points = [f"{v + offsets['v']}/{uv + offsets['vt']}/{n + offsets['vn']}" for v, uv, n in face["points"]]
        model.lines.append("f " + " ".join(points) + "\n")
    target = out / "models/maps/ares/ares_hall.obj"
    model.write(target)

    # Existing materials are reused. Extend the material dictionary and remaps; leave physics definitions byte-for-byte.
    mtl = original.with_suffix(".mtl").read_text()
    existing = set(re.findall(r"^newmtl (\S+)", mtl, flags=re.M))
    required = sorted(set(replacement.polygons) - existing)
    target.with_suffix(".mtl").write_text(mtl + "".join(f"newmtl {p}\nKd 1 1 1\nd 1\n" for p in required))
    vmdl = original.with_suffix(".vmdl").read_text()
    start = vmdl.index("[", vmdl.index("remaps =")) + 1
    end = vmdl.index("]", start)
    remaps = vmdl[start:end].rstrip()
    remaps += ",\n" + "\n".join(f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "materials/ares/{p}.vmat" }},' for p in required)
    remaps = remaps.rstrip(",") + "\n\t\t\t\t\t\t"
    updated = vmdl[:start] + remaps + vmdl[end:]
    physics = vmdl[vmdl.index('_class = "PhysicsShapeList"'):]
    if updated[updated.index('_class = "PhysicsShapeList"'):] != physics:
        raise ValueError("Collision definitions changed")
    target.with_suffix(".vmdl").write_text(updated)
    report = {"doors": summary, "triangles_before": len(model.faces), "old_hatch_triangles_removed": len(removed),
              "new_hatch_triangles": added, "triangles_after": len(model.faces) - len(removed) + added,
              "existing_materials_added_to_hall": required, "collision_definitions_unchanged": True,
              "unrelated_faces_unchanged": True, "before_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
              "after_sha256": hashlib.sha256(target.read_bytes()).hexdigest()}
    (out.parent / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args()
    stage(args.out, args.source_root)
