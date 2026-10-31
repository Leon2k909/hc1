"""Temporary models for the before/after in s&box: python cut_compare.py <project root>

Writes shooting_bench_v2/compare/: range_no_bench, the range with its four old benches cut out, and old_bench, the old bench at the 25 m lane on its own.
The game's own gunsmith_range model isn't touched. The old OBJ's axes are (-world y, z, world x).
"""
import os
import sys

ROOT = sys.argv[1]
SRC = os.path.join(ROOT, "Assets/models/gunsmith_range")
OUT = os.path.join(SRC, "shooting_bench_v2/compare")
FOLDER = "models/gunsmith_range/shooting_bench_v2/compare"
LANES = (-450.0, -150.0, 150.0, 450.0)
KEEP_LANE = -150.0
os.makedirs(OUT, exist_ok=True)

lines = open(os.path.join(SRC, "gunsmith_range.obj"), encoding="utf-8").read().splitlines()
verts = [tuple(map(float, l.split()[1:4])) for l in lines if l.startswith("v ")]


def lane_of(a):
    for lane in LANES:
        if abs(-a - lane) < 90.0:
            return lane
    return None


def in_leg(v):
    a, b, c = v
    y, z, x = -a, b, c
    if not (-0.01 <= z <= 30.01):
        return False
    if min(abs(x + 29.0), abs(x + 9.0)) > 2.01:
        return False
    return any(abs(abs(y - lane) - 76.0) <= 2.01 for lane in LANES)


head = [l for l in lines if not l.startswith("f ") and not l.startswith("usemtl")]
no_bench, old_bench = [], []
current = None
counts = [0, 0]
for line in lines:
    if line.startswith("usemtl"):
        current = line
        no_bench.append(line)
        old_bench.append(line)
    elif line.startswith("f "):
        idx = [int(t.split("/")[0]) - 1 for t in line.split()[1:]]
        points = [verts[i] for i in idx]
        name = current.split()[1]
        is_old = name.startswith("bench_oak") or (name == "rw_steel_dark" and all(in_leg(p) for p in points))
        if is_old:
            counts[0] += 1
            if lane_of(points[0][0]) == KEEP_LANE:
                old_bench.append(line)
                counts[1] += 1
        else:
            no_bench.append(line)


def without_empty_materials(body):
    """The OBJ loader refuses a usemtl with no faces after it at the end of a file."""
    kept = []
    for k, line in enumerate(body):
        if line.startswith("usemtl") and (k + 1 == len(body) or body[k + 1].startswith("usemtl")):
            continue
        kept.append(line)
    return kept


for name, body in (("range_no_bench", no_bench), ("old_bench", old_bench)):
    with open(os.path.join(OUT, name + ".obj"), "w", newline="\n", encoding="utf-8") as h:
        h.write("\n".join(head + without_empty_materials(body)) + "\n")
    with open(os.path.join(OUT, "gunsmith_range.mtl"), "w", newline="\n") as h:
        h.write(open(os.path.join(SRC, "gunsmith_range.mtl"), encoding="utf-8").read())
    vmdl = open(os.path.join(SRC, "gunsmith_range.vmdl"), encoding="utf-8").read()
    start = vmdl.index('_class = "PhysicsShapeList"')
    start = vmdl.rindex("{", 0, start)
    # The old file's physics list runs to its closing brace; a compare model doesn't need it.
    depth, i = 0, start
    while True:
        if vmdl[i] == "{":
            depth += 1
        elif vmdl[i] == "}":
            depth -= 1
            if depth == 0:
                break
        i += 1
    end = vmdl.index(",", i) + 1 if vmdl[i + 1 : i + 3].strip().startswith(",") else i + 1
    vmdl = vmdl[:start] + vmdl[end:]
    vmdl = vmdl.replace("models/gunsmith_range/gunsmith_range.obj", f"{FOLDER}/{name}.obj")
    with open(os.path.join(OUT, name + ".vmdl"), "w", newline="\n", encoding="utf-8") as h:
        h.write(vmdl)
print("old faces cut", counts[0], "kept at the 25 m lane", counts[1])
