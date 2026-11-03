"""File-level checks on the exported desk: python verify_desk.py. Exits 1 on a failure.

Fires rays at LOD 0 from where a camera can stand and fails if one passes through the desk's shell, which is what a wrongly
dropped hidden face looks like: it found the worktop's missing underside. Also checks the footprint, the materials, and that
the map has the four new desks and not the old ones.
"""
import json
import os
import sys

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
MODEL = os.path.join(ROOT, "Assets", "models", "props", "spillway", "control_desk_v2")
fails = []


def load(path):
    v, tris = [], {}
    cur = None
    for line in open(path, encoding="utf8"):
        if line.startswith("v "):
            v.append(line.split()[1:4])
        elif line.startswith("usemtl"):
            cur = line.split()[1]
        elif line.startswith("f "):
            tris.setdefault(cur, []).append([int(t.split("/")[0]) - 1 for t in line.split()[1:]])
    v = np.array(v, float)[:, [2, 0, 1]]  # OBJ is engine (Y, Z, X).
    return v, {k: np.array(f) for k, f in tris.items()}


def first_hit(origin, direction, tri):
    """Moller-Trumbore. Returns (distance, faces the ray) of the nearest hit, whichever way the triangle faces."""
    a, b, c = tri[:, 0], tri[:, 1], tri[:, 2]
    e1, e2 = b - a, c - a
    p = np.cross(direction, e2)
    det = (e1 * p).sum(1)
    ok = np.abs(det) > 1e-9
    inv = np.where(ok, 1 / np.where(ok, det, 1), 0)
    s = origin - a
    u = (s * p).sum(1) * inv
    q = np.cross(s, e1)
    w = (q * direction).sum(1) * inv
    t = (q * e2).sum(1) * inv
    hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-4)
    if not hit.any():
        return None, None
    i = np.where(hit)[0][np.argmin(t[hit])]
    return float(t[i]), bool(det[i] > 0)


v, groups = load(os.path.join(MODEL, "control_desk_lod0.obj"))
low, high = v.min(0), v.max(0)
print("bounds", low.round(2).tolist(), high.round(2).tolist())
if np.any(np.abs(low[:2] - (-35, -60)) > 0.01) or np.any(np.abs(high[:2] - (35, 60)) > 0.01) or abs(low[2]) > 0.01 or high[2] > 87.5:
    fails.append("outside the old desk's footprint or height")
if set(groups) != {"cd_body", "cd_panel", "cd_glow"}:
    fails.append(f"materials: {sorted(groups)}")
tri = v[np.concatenate(list(groups.values()))]

# Rays that must stop on a face turned towards them. Starts in the room; each aims through the desk.
aims = {
    "kneehole ceiling": ((60.0, 0.0, 8.0), (15.0, 0.0, 30.0)),
    "kneehole ceiling, left": ((60.0, -14.0, 10.0), (20.0, -14.0, 30.0)),
    "worktop from above": ((15.0, 0.0, 70.0), (15.0, 0.0, 30.0)),
    "worktop's front overhang from below": ((60.0, -40.0, 6.0), (33.0, -40.0, 29.5)),
    "left pedestal door": ((70.0, -40.0, 14.0), (20.0, -40.0, 14.0)),
    "right drawers": ((70.0, 40.0, 14.0), (20.0, 40.0, 14.0)),
    "modesty panel": ((70.0, 4.0, 14.0), (-20.0, 4.0, 14.0)),
    "left end": ((0.0, -90.0, 14.0), (0.0, -30.0, 14.0)),
    "right end": ((0.0, 90.0, 14.0), (0.0, 30.0, 14.0)),
    "left cheek": ((-20.0, -90.0, 45.0), (-20.0, -30.0, 45.0)),
    "right cheek": ((-20.0, 90.0, 45.0), (-20.0, 30.0, 45.0)),
    "board": ((30.0, -20.0, 70.0), (-10.0, -20.0, 40.0)),
    "meters": ((30.0, 5.0, 53.0), (-25.0, 5.0, 53.0)),
    "hood from above": ((-25.0, 50.0, 90.0), (-25.0, 50.0, 55.0)),
    "hood from below, front": ((40.0, 50.0, 40.0), (-18.0, 50.0, 57.7)),
    "main screen": ((40.0, 0.0, 72.0), (-22.0, 0.0, 72.0)),
    "left screen": ((30.0, -36.0, 70.0), (-23.0, -36.0, 70.0)),
    "main screen's bottom edge from below": ((40.0, 6.0, 30.0), (-20.2, 6.0, 60.6)),
    "rear panel": ((-90.0, 0.0, 30.0), (-30.0, 0.0, 30.0)),
}
for name, (a, b) in aims.items():
    origin, target = np.array(a), np.array(b)
    d = (target - origin) / np.linalg.norm(target - origin)
    dist, front = first_hit(origin, d, tri)
    state = "NO HIT" if dist is None else f"{dist:.1f} in, {'front' if front else 'BACK'} face"
    print(f"  {name}: {state}")
    if dist is None or not front:
        fails.append(name)

# The old desks have gone from the map, and four new ones stand where they were, each with a collider.
scene = json.load(open(os.path.join(ROOT, "Assets", "scenes", "maps", "spillway", "spillway.scene"), encoding="utf8"))
root = next(g for g in scene["GameObjects"] if g.get("Name") == "Spillway")
desks = [c for c in root["Children"] if c["Name"].startswith("Control Desk")]
if sorted(c["Position"] for c in desks) != sorted(f"1275,{-e},236" for e in (-190, 60, 310, 500)):
    fails.append("the scene's desks: " + str([c["Position"] for c in desks]))
for desk in desks:
    if desk["Rotation"] != "0,0,1,0" or sorted(c["__type"] for c in desk["Components"]) != ["Sandbox.ModelCollider", "Sandbox.ModelRenderer"]:
        fails.append(desk["Name"] + " isn't turned or built as expected")
    for component in desk["Components"]:
        if component["Model"]["Path"] != "models/props/spillway/control_desk_v2/control_desk.vmdl":
            fails.append(desk["Name"] + " draws another model")
control = open(os.path.join(ROOT, "Assets", "models", "maps", "spillway", "spillway_control.obj"), encoding="utf8").read()
if "usemtl rv_desk" in control or "usemtl rv_screens" in control:
    fails.append("the old desks are still in spillway_control.obj")
vmdl = open(os.path.join(ROOT, "Assets", "models", "maps", "spillway", "spillway_control.vmdl"), encoding="utf8").read()
if "dimensions = [ 120.0000, 70.0000, 34.0000 ]" in vmdl:
    fails.append("the old desks' collision is still in spillway_control.vmdl")
script = open(os.path.join(ROOT, "Tools", "spillway_map.py"), encoding="utf8").read()
if '"schematic"' in script or "control_desk_v2" not in script:
    fails.append("the map script would bring the old desks back")

export = json.load(open(os.path.join(ROOT, "output", "asset-improvement-20261030", "spillway-desk", "export.json")))
print("triangles", export["triangles"])
print("FAILED: " + "; ".join(fails) if fails else "all checks pass")
sys.exit(1 if fails else 0)
