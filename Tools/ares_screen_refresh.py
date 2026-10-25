"""Stage only the Ares screen UVs and the two raised Red Planet signs, from the existing installed OBJ sources.

No scene, collision hull, material layout or unrelated mesh is regenerated. The geometry report records exactly
which vertex/UV lines changed. Import the stage through Sources/Ares/screens/import.cs.txt.
This is a one-time migration of the original meshes. To reproduce it after installation, pass
--source-root output/ares/screens-20261020/before, which holds the unmodified OBJ sources.
"""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent


class Obj:
    def __init__(self, path):
        self.lines = path.read_text().splitlines(keepends=True)
        self.values = {key: [None] for key in ("v", "vt", "vn")}
        self.locations = {key: [None] for key in self.values}
        self.faces = []
        material = None
        for line_index, line in enumerate(self.lines):
            parts = line.split()
            if not parts:
                continue
            kind = parts[0]
            if kind in self.values:
                self.locations[kind].append(line_index)
                self.values[kind].append(tuple(map(float, parts[1:])))
            elif kind == "usemtl":
                material = parts[1]
            elif kind == "f":
                self.faces.append({"line": line_index, "material": material,
                                   "points": [tuple(map(int, point.split("/"))) for point in parts[1:]]})
        self.edited = {"v": set(), "vt": set()}
        self.repaints = {}

    def assign(self, kind, index, value):
        self.values[kind][index] = tuple(value)
        self.edited[kind].add(index)
        digits = 3 if kind == "v" else 5
        self.lines[self.locations[kind][index]] = kind + " " + " ".join(f"{x:.{digits}f}" for x in value) + "\n"

    def quads(self, material):
        groups = defaultdict(list)
        for face in self.faces:
            if face["material"] == material:
                normal_ids = {point[2] for point in face["points"]}
                if len(normal_ids) != 1:
                    raise ValueError("Expected flat screen/sign quads")
                groups[next(iter(normal_ids))].append(face)
        for faces in groups.values():
            vertices = {point[0] for face in faces for point in face["points"]}
            uv_ids = {point[1] for face in faces for point in face["points"]}
            if len(faces) != 2 or len(vertices) != 4 or len(uv_ids) != 4:
                raise ValueError("Unexpected screen/sign triangulation")
            yield faces, vertices, uv_ids

    def write(self, path):
        # Restore the previous paint after a reassigned triangle, keeping all existing indices and topology.
        for line_index, paint in self.repaints.items():
            self.lines[line_index] = f"usemtl {paint}\n" + self.lines[line_index] + "usemtl ar_screens\n"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(self.lines), newline="\n")


def screens(model, pump=False):
    consoles = wall = readers = repainted = 0
    for faces, vertices, uv_ids in model.quads("ar_screens"):
        points = np.array([model.values["v"][index] for index in vertices])
        heights = points[:, 1]  # map_kit writes OBJ as (-east, height, north).
        if not pump:
            if np.isclose(heights.min(), 36) and np.isclose(heights.max(), 64):
                u_values = [model.values["vt"][index][0] for index in uv_ids]
                mirror = min(u_values) + max(u_values)
                for index in uv_ids:
                    u, v = model.values["vt"][index]
                    model.assign("vt", index, (mirror - u, v))
                consoles += 1
            else:
                if not (np.isclose(heights.min(), 80) and np.isclose(heights.max(), 130)):
                    raise ValueError("Unrecognised monitor geometry")
                wall += 1
            continue
        normal = np.array(model.values["vn"][faces[0]["points"][0][2]])
        centre = points.mean(axis=0)
        width = max(np.linalg.norm(a[[0, 2]] - b[[0, 2]]) for a in points for b in points)
        front = np.isclose(heights.min(), 20) and np.isclose(heights.max(), 44) and np.isclose(width, 20, atol=.01)
        front &= np.dot(normal[[0, 2]], centre[[0, 2]]) > 0
        if not front:
            for face in faces:
                model.repaints[face["line"]] = "ar_steel"
                repainted += 1
            continue
        # The reader faces out from the processing column. Its right is the plan normal rotated 90 degrees.
        facing = np.array((-normal[0], normal[2]))
        right = np.array((-facing[1], facing[0]))
        along = {index: float(np.dot(np.array((-model.values["v"][index][0], model.values["v"][index][2])), right))
                 for index in vertices}
        lo, hi = min(along.values()), max(along.values())
        for face in faces:
            for vertex, uv_index, _ in face["points"]:
                u = .5 + .25 * (along[vertex] - lo) / (hi - lo)  # screen6, coolant loops
                v = .5 * (model.values["v"][vertex][1] - 20) / 24
                model.assign("vt", uv_index, (u, v))
        readers += 1
    return {"consoles_corrected": consoles, "wall_monitors": wall, "pump_readers_mapped": readers,
            "reader_edge_triangles_changed_to_steel": repainted}


def posters(model):
    records = []
    for x, north, old in ((-1099.0, -330.0, 120.0), (1099.0, 330.0, 130.0)):
        selected = set()
        for face in model.faces:
            if face["material"] not in ("ar_signs", "ar_steel"):
                continue
            ids = [point[0] for point in face["points"]]
            points = np.array([model.values["v"][index] for index in ids])
            # Front picture at |x| 1098.95, one-inch backing at |x| 1099..1100.
            within = (np.abs(points[:, 0] - x) <= 1.01) & (np.abs(points[:, 2] - north) <= 75.51)
            within &= np.abs(points[:, 1] - old) <= 28.51
            if np.all(within):
                selected.update(ids)
        if len(selected) != 28:
            raise ValueError(f"Expected the four picture and 24 backing vertices for poster {x}: {len(selected)}")
        for index in selected:
            p = list(model.values["v"][index])
            p[1] += 163 - old
            model.assign("v", index, p)
        records.append({"old_centre_height": old, "new_centre_height": 163, "vertices": len(selected),
                        "bottom": 135, "top": 191, "monitor_top": 130, "ceiling": 192})
    return records


def stage(out, source_root):
    report = {}
    pending = []
    for name, expected in (("ares_hall", (6, 6, 0)), ("ares_dressing", (2, 0, 0)), ("ares_reactor", (0, 0, 4))):
        relative = Path("Assets/models/maps/ares") / f"{name}.obj"
        original = source_root / relative
        source = Obj(original)
        summary = screens(source, pump=name == "ares_reactor")
        actual = tuple(summary[key] for key in ("consoles_corrected", "wall_monitors", "pump_readers_mapped"))
        if actual != expected:
            raise ValueError(f"Unexpected monitor counts in {name}: {actual}")
        if name == "ares_dressing":
            summary["raised_posters"] = posters(source)
        elif source.edited["v"]:
            raise ValueError("Screen fixes must not move any other geometry")
        staged = out / "models/maps/ares" / original.name
        summary.update({"triangles": len(source.faces), "changed_vertices": len(source.edited["v"]),
                        "changed_uvs": len(source.edited["vt"]),
                        "before_sha256": hashlib.sha256(original.read_bytes()).hexdigest()})
        report[name] = summary
        pending.append((name, source, staged))
    # Validate every baseline before replacing any staged mesh. Already raised posters reject a second migration.
    for name, source, staged in pending:
        source.write(staged)
        report[name]["after_sha256"] = hashlib.sha256(staged.read_bytes()).hexdigest()
    out.mkdir(parents=True, exist_ok=True)
    (out.parent / "geometry.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-root", type=Path, default=ROOT)
    args = parser.parse_args()
    stage(args.out, args.source_root)
