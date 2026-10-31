"""Swap Railhead's station bins for station_bin_v2 without regenerating the map: python install_bins.py <project root> [--write]

The old bins are merged into the checked-in railhead_dress_* OBJs, and a full map run rewrites far more than the bins. So this finds each bin there by its
middle colour plate, which also gives its facing, cuts only its faces and leaves its collision alone, since that's in the vmdl. Then it adds a "Station
Bins" group to the scene, which is what railhead_bins.scene_group() makes on a full run. It stops before writing anything if a bin doesn't have the faces
it should. Without --write it only reports. Run it with Railhead closed in the editor: a file watcher compiles the rewritten OBJs by itself. It has run: it
stops if there are no old bins left, and placements.json holds where they were.
"""
import collections
import json
import math
import os
import pathlib
import sys
import tempfile

import numpy as np
from scipy.spatial import cKDTree

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
WRITE = "--write" in sys.argv[2:]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import railhead_bins as B  # noqa: E402
import railhead_furniture as FU  # noqa: E402
import railhead_map as M  # noqa: E402
import railhead_prop_materials as PM  # noqa: E402
import railhead_props as P  # noqa: E402

DIR = os.path.join(ROOT, "Assets", "models", "maps", "railhead")
PLACEMENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "placements.json")
ZONES = ("railhead_dress_centre", "railhead_dress_east", "railhead_dress_west")
PAINTS = {"rw_steel_dark", "rw_stainless", "rw_black", "rw_rubber", "rw_prop_signs"}
OLD_TRIANGLES = 280
# The old model's bounds, in its own frame: x towards its front, y across it, z up.
FRONT, BACK, HALF, TALL = 9.65, -8.75, 20.15, 39.67
PLATE_OFFSET, PLATE_Z = 8.35, 17.6


def rect(name):
    u0, v0, u1, v1 = PM.rect_uv(name)
    return min(u0, u1), min(v0, v1), max(u0, u1), max(v0, v1)


PACK = rect("bin_pack")
PAPER = rect("bin_paper")


def read(zone):
    path = os.path.join(DIR, zone + ".obj")
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    v = np.array([line[2:].split()[:3] for line in lines if line.startswith("v ")], float)[:, [2, 0, 1]]
    vt = np.array([line[3:].split()[:2] for line in lines if line.startswith("vt ")], float)
    return path, lines, v, vt


def in_rect(uv, r):
    return r[0] - 1e-3 <= uv[0] <= r[2] + 1e-3 and r[1] - 1e-3 <= uv[1] <= r[3] + 1e-3


def cluster(points):
    """Whole plates of one kind from their triangles' corners. A plate is 7.2 square, so its corners are all within 10.2 of each other, and bins stand further apart."""
    groups = []
    for p in points:
        for g in groups:
            if np.linalg.norm(g[0] - p) < 11.0:
                g.append(p)
                break
        else:
            groups.append([p])
    return [np.unique(np.array(g).round(3), axis=0) for g in groups]


zones = {}
pack_tris, paper_tris = [], []
for zone in ZONES:
    path, lines, v, vt = read(zone)
    zones[zone] = (path, lines, v)
    current = None
    for line in lines:
        if line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current == "rw_prop_signs":
            tokens = [t.split("/") for t in line.split()[1:]]
            uvs = vt[[int(t[1]) - 1 for t in tokens]]
            if all(in_rect(u, PACK) for u in uvs):
                pack_tris.append(v[[int(t[0]) - 1 for t in tokens]])
            elif all(in_rect(u, PAPER) for u in uvs):
                paper_tris.append(v[[int(t[0]) - 1 for t in tokens]])
    print(zone, "read", flush=True)

papers = [g.mean(0) for g in cluster([p for t in paper_tris for p in t])]
bins = []
for group in cluster([p for t in pack_tris for p in t]):
    centre = (group.min(0) + group.max(0)) / 2
    # The plate lies flat on the front, so the narrow axis of its corners is the way it faces, and the paper plate 13.3 away says which way across.
    spread = group.max(0) - group.min(0)
    across = np.array((1.0, 0.0, 0.0)) if spread[0] > spread[1] else np.array((0.0, 1.0, 0.0))
    paper = min(papers, key=lambda p: np.linalg.norm(p - centre))
    to_paper = paper - centre
    if abs(np.linalg.norm(to_paper) - 13.3) > 0.2 or abs(abs(np.dot(to_paper, across)) - 13.3) > 0.2:
        raise SystemExit(f"The plate at {centre.round(1)} has no paper plate 13.3 across from it: nothing written.")
    # The model's paper bay is at its -Y, and yaw turns +X to its front and +Y to the front's left.
    left = -to_paper / 13.3
    front = np.array((left[1], -left[0], 0.0))
    position = centre - front * PLATE_OFFSET
    position[2] = centre[2] - PLATE_Z
    bins.append((position.round(3), round(math.degrees(math.atan2(front[1], front[0])) % 360.0, 3)))
bins.sort(key=lambda b: (b[0][0], b[0][1], b[0][2]))
if not bins:
    raise SystemExit(f"No old bins left in the OBJs, so this has already run. {PLACEMENTS} holds where they were.")
print(len(bins), "bins", flush=True)
for at, yaw in bins:
    print("  at", at.tolist(), "yaw", yaw, flush=True)

placed = list(bins)
frames = [(at, np.array((math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))), np.array((-math.sin(math.radians(yaw)), math.cos(math.radians(yaw))))) for at, yaw in bins]
grid = collections.defaultdict(list)
for k, (at, _, _) in enumerate(frames):
    for gx in range(int(at[0] // 64) - 1, int(at[0] // 64) + 2):
        for gy in range(int(at[1] // 64) - 1, int(at[1] // 64) + 2):
            grid[(gx, gy)].append(k)

# The old bin from the map's own code, at yaw 0 (read_old.py).
model = K.Model()
FU.bin(model, P.frame_for(0.0, 0.0, 0.0, "+n"))
for paint in model.polygons:
    model.tile_overrides[paint] = 64.0
with tempfile.TemporaryDirectory() as scratch:
    target = pathlib.Path(scratch) / "old_bin.obj"
    K.write_obj(target, model, "old_bin")
    old_corners = cKDTree(np.array([line[2:].split()[:3] for line in open(target, encoding="utf-8") if line.startswith("v ")], float)[:, [2, 0, 1]])

counts = [0] * len(frames)
out = {}
for zone, (path, lines, v) in zones.items():
    current = None
    drop = set()
    for n, line in enumerate(lines):
        if line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in PAINTS:
            tokens = line.split()[1:]
            q = v[[int(t.split("/")[0]) - 1 for t in tokens]]
            for k in grid.get((int(q[0, 0] // 64), int(q[0, 1] // 64)), ()):
                at, forward, left = frames[k]
                d = q - at
                x, y, z = d[:, :2] @ forward, d[:, :2] @ left, d[:, 2]
                if x.min() > BACK and x.max() < FRONT and np.abs(y).max() < HALF and z.min() > -0.05 and z.max() < TALL:
                    # Inside its bounds isn't enough: a cab rank bollard stands within them. Every corner has to be one of the old bin's.
                    if old_corners.query(np.column_stack((x, y, z)))[0].max() < 0.03:
                        drop.add(n)
                        counts[k] += len(tokens) - 2
                        break
    # A usemtl left with no faces goes too.
    kept = [line for n, line in enumerate(lines) if n not in drop]
    final = []
    for n, line in enumerate(kept):
        if line.startswith("usemtl"):
            following = next((x for x in kept[n + 1 :] if x.startswith(("f ", "usemtl"))), "")
            if not following.startswith("f "):
                continue
        final.append(line)
    out[path] = (final, len(drop))
    print(zone, "faces to cut:", len(drop), flush=True)

print("triangles per bin:", collections.Counter(counts), flush=True)
wrong = [(bins[k][0].tolist(), c) for k, c in enumerate(counts) if c != OLD_TRIANGLES]
if wrong:
    raise SystemExit(f"These bins don't have {OLD_TRIANGLES} triangles to cut: {wrong}. Nothing written.")

scene_file = pathlib.Path(M.SCENE_FILE)
scene = json.loads(scene_file.read_text(encoding="utf-8"))
station = next(o for o in scene["GameObjects"] if o.get("Name") == "Station")
group = B.scene_group(placed)
names = [o.get("Name") for o in station["Children"]]
print("scene:", len(group["Children"]), "bins, group already there:", "Station Bins" in names, flush=True)
if not WRITE:
    print("dry run: nothing written", flush=True)
    raise SystemExit(0)

# The scene first: once the OBJs are cut, their plates can't say where the bins were any more.
with open(PLACEMENTS, "w", encoding="utf-8", newline="\n") as h:
    json.dump([[at.tolist(), yaw] for at, yaw in bins], h, indent=2)
if "Station Bins" in names:
    station["Children"][names.index("Station Bins")] = group
else:
    station["Children"].insert(names.index("Dressing Glass") + 1, group)
K.write_text(scene_file, json.dumps(scene, indent=2), newline=None)
for path, (final, dropped) in out.items():
    if dropped:
        temp = path + ".installing"
        with open(temp, "w", encoding="utf-8", newline="") as h:
            h.writelines(final)
            h.flush()
            os.fsync(h.fileno())
        os.replace(temp, path)
print("written", flush=True)
