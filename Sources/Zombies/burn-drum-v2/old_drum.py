"""Cut one old drum out of Riverside's merged model, for a matched before: python old_drum.py <project root> <work dir>

The pad drum: riverside_parts.drum at plan (48, -18) on the pad, z 96, in riverside_pad.obj. Written about its own axis and
foot in the same axis order, with its own material names, UVs and normals. Reads only.
"""
import os
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
SOURCE = os.path.join(ROOT, "Assets", "models", "maps", "riverside", "riverside_pad.obj")
AXIS = np.array((-18.0, -48.0, 96.0))  # Engine (x, y, z): plan (e, n, z) is (n, -e, z).
WANTED = {"rs_drum_blue", "rs_rust", "rs_drum_inside", "rs_ember"}

positions, uvs, normals = [], [], []
faces = []
current = None
for line in open(SOURCE, encoding="utf-8"):
    tag = line[:2]
    if tag == "v ":
        a, b, c = map(float, line[2:].split()[:3])
        positions.append((c, a, b))
    elif tag == "vt":
        uvs.append(line[3:].strip())
    elif tag == "vn":
        normals.append(line[3:].strip())
    elif line.startswith("usemtl"):
        current = line.split()[1]
    elif tag == "f " and current in WANTED:
        faces.append((current, line.split()[1:]))
p = np.array(positions) - AXIS

kept = {}
for mat, toks in faces:
    idx = [int(t.split("/")[0]) - 1 for t in toks]
    q = p[idx]
    if np.hypot(q[:, 0], q[:, 1]).max() < 13.0 and q[:, 2].min() > -0.5 and q[:, 2].max() < 35.5:
        kept.setdefault(mat, []).append(toks)

lines, tris = [], 0
out_v, out_t, out_n, remap_v, remap_t, remap_n = [], [], [], {}, {}, {}
for mat, polys in kept.items():
    lines.append(f"usemtl {mat}\n")
    for toks in polys:
        tris += len(toks) - 2
        row = []
        for t in toks:
            a, b, c = (t.split("/") + ["", ""])[:3]
            va = remap_v.setdefault(a, len(remap_v) + 1)
            if va == len(remap_v) and len(out_v) < va:
                q = p[int(a) - 1]
                out_v.append(f"v {q[1]:.5f} {q[2]:.5f} {q[0]:.5f}\n")
            vb = remap_t.setdefault(b, len(remap_t) + 1)
            if len(out_t) < vb:
                out_t.append(f"vt {uvs[int(b) - 1]}\n")
            vc = remap_n.setdefault(c, len(remap_n) + 1)
            if len(out_n) < vc:
                out_n.append(f"vn {normals[int(c) - 1]}\n")
            row.append(f"{va}/{vb}/{vc}")
        lines.append("f " + " ".join(row) + "\n")
with open(os.path.join(WORK, "old_drum.obj"), "w", newline="\n") as h:
    h.writelines(out_v + out_t + out_n + lines)
print("old drum:", {k: len(v) for k, v in kept.items()}, "triangles", tris, flush=True)
kept_points = np.array([[float(x) for x in s.split()[1:]] for s in out_v])[:, [2, 0, 1]]
print("bounds", kept_points.min(0).round(2), kept_points.max(0).round(2), flush=True)
