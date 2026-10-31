"""Cut the old teddy out of Riverside's merged model, for a matched before: python old_teddy.py <project root> <work dir>

riverside_parts.teddy in the mud by the dog run's gate, in riverside_pad.obj. Written about its own foot, turned so it faces local +x as the new one
does, in the same OBJ axis order, with its own material names, UVs and normals. Reads only.
"""
import os
import sys

import numpy as np

ROOT, WORK = sys.argv[1], sys.argv[2]
SOURCE = os.path.join(ROOT, "Assets", "models", "maps", "riverside", "riverside_pad.obj")
WANTED = {"rs_teddy", "rs_teddy_dark"}

# Tools/riverside_map.py: P.teddy( m, ( -24, -215 ), ( 0.45, -0.9 ), gz ). Plan (e, n) is engine (n, -e).
facing_plan = np.array((0.45, -0.9))
facing_plan /= np.linalg.norm(facing_plan)
FOOT = np.array((-215.0, 24.0, 96.0))
FACING = np.array((facing_plan[1], -facing_plan[0]))
SIDE = np.array((-FACING[1], FACING[0]))
print("foot", FOOT, "facing", FACING.round(3), "yaw %.2f" % np.degrees(np.arctan2(FACING[1], FACING[0])), flush=True)

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
local = np.column_stack((P[:, :2] @ FACING, P[:, :2] @ SIDE, P[:, 2]))
N = np.array(normals)
nlocal = np.column_stack((N[:, :2] @ FACING, N[:, :2] @ SIDE, N[:, 2]))

kept = {}
for mat, toks in faces:
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
with open(os.path.join(WORK, "old_teddy.obj"), "w", newline="\n") as h:
    h.writelines(out_v + out_t + out_n + lines)
pts = np.array([[float(x) for x in s.split()[1:]] for s in out_v])[:, [2, 0, 1]]
print("old teddy:", {k: len(v) for k, v in kept.items()}, "triangles", tris, flush=True)
print("bounds", pts.min(0).round(2), pts.max(0).round(2), flush=True)
