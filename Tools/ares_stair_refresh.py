"""Stage the Ares stair surface fix without regenerating the hall, scene, collision or previous visual edits.

This migrates the original four 28-step flights. Reproduce after installation with
--source-root output/ares/stairs-20261020/before. Import the staged hall OBJ through Sources/Ares/stairs/import.cs.txt.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

import ares_map as A
from ares_screen_refresh import Obj

ROOT = Path(__file__).resolve().parent.parent


def flat_quads(model):
    groups = defaultdict(list)
    for face in model.faces:
        if face["material"] not in ("ar_hazard", "ar_steel", "ar_grating"):
            continue
        normals = {point[2] for point in face["points"]}
        if len(normals) == 1:
            groups[(face["material"], next(iter(normals)))].append(face)
    for (paint, normal), faces in groups.items():
        vertices = {p[0] for face in faces for p in face["points"]}
        if len(faces) != 2 or len(vertices) != 4:
            continue
        points = np.array([model.values["v"][i] for i in vertices])
        # The source OBJ coordinates are (-east, height, north), not engine world coordinates.
        plan = np.c_[-points[:, 0], points[:, 2], points[:, 1]]
        yield {"paint": paint, "faces": faces, "vertices": vertices,
               "normal": np.array(model.values["vn"][normal]), "points": plan,
               "lo": plan.min(axis=0), "hi": plan.max(axis=0)}


def same_bounds(quad, lo, hi):
    return np.allclose(quad["lo"], lo, atol=.0015, rtol=0) and np.allclose(quad["hi"], hi, atol=.0015, rtol=0)


def stage(out, source_root):
    original = source_root / "Assets/models/maps/ares/ares_hall.obj"
    model = Obj(original)
    quads = list(flat_quads(model))
    removed = set()
    flights = []
    count = round(A.G / 7.4)
    for location, across, along in (("hall", A.STAIR_E, A.STAIR_N), ("wing", A.WING_STAIR_E, A.WING_STAIR_N)):
        for side in (-1, 1):
            c0, c1 = sorted(side * c for c in across)
            s0, s1 = along
            local = [q for q in quads if np.all(q["lo"] >= np.array((c0, s0, 0)) - .0015)
                     and np.all(q["hi"] <= np.array((c1, s1, A.G + .13)) + .0015)]
            for k in range(count):
                sa, sb = s0 + (s1 - s0) * k / count, s0 + (s1 - s0) * (k + 1) / count
                top = A.G * (k + 1) / count
                lo, hi = np.array((c0, sa, top - 1.6)), np.array((c1, sa + 2, top + .05))
                nose = [q for q in local if q["paint"] == "ar_hazard" and np.all(q["lo"] >= lo - .0015)
                        and np.all(q["hi"] <= hi + .0015)]
                fronts = [q for q in local if q["paint"] == "ar_steel"
                          and same_bounds(q, (c0, sa, top - 1.5), (c1, sa, top))]
                tops = [q for q in local if q["paint"] == "ar_grating"
                        and same_bounds(q, (c0, sa, top), (c1, sb, top))]
                if (len(nose), len(fronts), len(tops)) != (6, 1, 1):
                    raise ValueError(f"Expected original overlapping stair surfaces at {location}/{side}/{k}: "
                                     f"{len(nose)}, {len(fronts)}, {len(tops)}")
                # The tread front is completely hidden by the yellow face. Remove the competing steel triangles.
                removed.update(face["line"] for face in fronts[0]["faces"])
                for quad in nose:
                    if abs(quad["normal"][0]) > .99 or quad["normal"][1] < -.99:
                        # Ends coincide with the steel stringers; the underside is owned by the steel tread.
                        removed.update(face["line"] for face in quad["faces"])
                        continue
                    for index in quad["vertices"]:
                        value = list(model.values["v"][index])
                        if np.isclose(value[1], top - 1.6, atol=.0015, rtol=0):
                            value[1] = top - 1.5  # Meet the steel riser without the previous 0.1-inch overlap.
                        elif np.isclose(value[1], top + .05, atol=.0015, rtol=0):
                            value[1] = top + .125
                        else:
                            raise ValueError("Unexpected nosing height")
                        model.assign("v", index, value)
                # Trim the grating's front two inches. Interpolate its UVs so the material's world scale is retained.
                quad = tops[0]
                for vertex in quad["vertices"]:
                    value = list(model.values["v"][vertex])
                    if not np.isclose(value[2], sa, atol=.0015, rtol=0):
                        continue
                    back = next(i for i in quad["vertices"] if np.isclose(model.values["v"][i][0], value[0], atol=.0015)
                                and np.isclose(model.values["v"][i][2], sb, atol=.0015))
                    uv_id = next(p[1] for f in quad["faces"] for p in f["points"] if p[0] == vertex)
                    back_uv = next(p[1] for f in quad["faces"] for p in f["points"] if p[0] == back)
                    ratio = 2 / (model.values["v"][back][2] - value[2])
                    uv = np.array(model.values["vt"][uv_id])
                    uv += ratio * (np.array(model.values["vt"][back_uv]) - uv)
                    value[2] = sa + 2
                    model.assign("v", vertex, value)
                    model.assign("vt", uv_id, uv)
            flights.append({"location": location, "side": side, "steps": count})
    if len(removed) != 896 or len(model.edited["v"]) != 1568 or len(model.edited["vt"]) != 224:
        raise ValueError(f"Unexpected change scope: {len(removed)} triangles, {len(model.edited['v'])} vertices, "
                         f"{len(model.edited['vt'])} UVs")
    for line in removed:
        model.lines[line] = ""
    destination = out / "models/maps/ares/ares_hall.obj"
    model.write(destination)
    report = {"flights": flights, "steps_fixed": 112, "coplanar_front_overlaps_removed": 112,
              "coplanar_nosing_end_quads_removed": 224, "overlapping_tread_tops_trimmed": 112,
              "hidden_nosing_bottom_quads_removed": 112,
              "triangles_before": len(model.faces), "triangles_after": len(model.faces) - len(removed),
              "triangles_removed": len(removed), "vertices_changed": len(model.edited["v"]),
              "uvs_changed": len(model.edited["vt"]), "collision_sources_changed": False,
              "before_sha256": hashlib.sha256(original.read_bytes()).hexdigest(),
              "after_sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}
    (out.parent / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    stage(args.out, args.source_root)
