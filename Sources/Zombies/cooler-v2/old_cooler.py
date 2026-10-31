"""Cut the old cooler out of Riverside's merged model, for a matched before: python old_cooler.py <project root> <work dir>

riverside_parts.cooler at the dog run's gate, in riverside_pad.obj. Written about its own foot, turned so its length is local x and
its open side local +y, as the new one is, in the same OBJ axis order, with its own material names, UVs and normals. Reads only.
Also crops the marker lettering from the signs atlas, so the new lid has the same words in the same hand.
"""
import os
import sys

import numpy as np
from PIL import Image

ROOT, WORK = sys.argv[1], sys.argv[2]
SOURCE = os.path.join(ROOT, "Assets", "models", "maps", "riverside", "riverside_pad.obj")
WANTED = {"rs_cooler", "rs_cooler_white", "rs_drum_inside", "rs_drum_red", "rs_alu", "rs_signs"}

# Tools/riverside_map.py: DOG_RUN and DOG_GATE give the gate, the cooler stands 10 out from it. Plan (e, n) is engine (n, -e).
a, b = np.array((-40.0, -195.0)), np.array((0.0, -40.0))
d = (b - a) / np.linalg.norm(b - a)
out = np.array((d[1], -d[0]))
gate = a + d * (5 + 50) / 2
foot_plan = gate + out * 10
along_plan = -d
side_plan = np.array((-along_plan[1], along_plan[0]))


def to_engine(p):
    return np.array((p[1], -p[0]))


FOOT = np.array((*to_engine(foot_plan), 96.0))
ALONG, SIDE = to_engine(along_plan), to_engine(side_plan)
print("foot", FOOT.round(2), "along", ALONG.round(3), "side", SIDE.round(3), flush=True)

positions, uvs, normals, faces = [], [], [], []
current = None
for line in open(SOURCE, encoding="utf-8"):
    tag = line[:2]
    if tag == "v ":
        p, q, r = map(float, line[2:].split()[:3])
        positions.append((r, p, q))
    elif tag == "vt":
        uvs.append(line[3:].strip())
    elif tag == "vn":
        p, q, r = map(float, line[3:].split()[:3])
        normals.append((r, p, q))
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif tag == "f " and current in WANTED:
        faces.append((current, line.split()[1:]))
P = np.array(positions) - FOOT
local = np.column_stack((P[:, 0] * ALONG[0] + P[:, 1] * ALONG[1], P[:, 0] * SIDE[0] + P[:, 1] * SIDE[1], P[:, 2]))
N = np.array(normals)
nlocal = np.column_stack((N[:, 0] * ALONG[0] + N[:, 1] * ALONG[1], N[:, 0] * SIDE[0] + N[:, 1] * SIDE[1], N[:, 2]))

kept = {}
for mat, toks in faces:
    idx = [int(t.split("/")[0]) - 1 for t in toks]
    q = local[idx]
    if np.abs(q[:, 0]).max() < 18.0 and np.abs(q[:, 1]).max() < 18.0 and q[:, 2].min() > -0.5 and q[:, 2].max() < 36.0:
        kept.setdefault(mat, []).append(toks)

lines, tris = [], 0
out_v, out_t, out_n, remap_v, remap_t, remap_n = [], [], [], {}, {}, {}
for mat, polys in kept.items():
    lines.append(f"usemtl {mat}\n")
    for toks in polys:
        tris += len(toks) - 2
        row = []
        for t in toks:
            pa, pb, pc = t.split("/")
            va = remap_v.setdefault(pa, len(remap_v) + 1)
            if len(out_v) < va:
                q = local[int(pa) - 1]
                out_v.append(f"v {q[1]:.5f} {q[2]:.5f} {q[0]:.5f}\n")
            vb = remap_t.setdefault(pb, len(remap_t) + 1)
            if len(out_t) < vb:
                out_t.append(f"vt {uvs[int(pb) - 1]}\n")
            vc = remap_n.setdefault(pc, len(remap_n) + 1)
            if len(out_n) < vc:
                q = nlocal[int(pc) - 1]
                out_n.append(f"vn {q[1]:.5f} {q[2]:.5f} {q[0]:.5f}\n")
            row.append(f"{va}/{vb}/{vc}")
        lines.append("f " + " ".join(row) + "\n")
with open(os.path.join(WORK, "old_cooler.obj"), "w", newline="\n") as h:
    h.writelines(out_v + out_t + out_n + lines)
pts = np.array([[float(x) for x in s.split()[1:]] for s in out_v])[:, [2, 0, 1]]
print("old cooler:", {k: len(v) for k, v in kept.items()}, "triangles", tris, flush=True)
print("bounds", pts.min(0).round(2), pts.max(0).round(2), flush=True)

atlas = Image.open(os.path.join(ROOT, "Assets", "materials", "riverside", "rs_signs_color.png")).convert("RGB")
print("atlas", atlas.size, flush=True)
crop = atlas.crop((2048, 0, 2048 + 1024, 640))
crop.save(os.path.join(WORK, "lid_lettering.png"))
