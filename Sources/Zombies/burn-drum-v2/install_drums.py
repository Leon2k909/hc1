"""Swap Riverside's drums for burn_drum_v2 without regenerating the map: python install_drums.py <project root>

Rerunning Tools/riverside_map.py isn't safe at the moment. The shared kit has changed since the map was last generated, so it rewrites
the ground, levee, pad and dressing and adds paints with no material. So this asks the map's own code where the drums are, cuts only
their faces out of the checked-in zone OBJs, leaves their hulls alone, and adds the same "Burn Drums" group to the scene that
riverside_map.py's write_scene makes. It stops before writing anything if a drum doesn't have the faces it should. Safe to rerun.
"""
import json
import os
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = sys.argv[1]
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import riverside_map as M  # noqa: E402

K, P = M.K, M.P
DRUM_PAINTS = {"rs_drum_blue", "rs_drum_red", "rs_rust", "rs_drum_inside", "rs_ember", "rs_ash"}
ZONES = ("riverside_pad", "riverside_store", "riverside_dressing")
EXPECTED = {True: 164, False: 152}

P.reset()
low, terrace, high = K.Model(), K.Model(), K.Model()
M.trailers(low, terrace, high)
M.store(K.Model())
M.pad(K.Model())
M.dressing(K.Model())
drums = [(name, K.to_world(position), variant) for name, position, variant, _ in P.BURN_DRUMS]
print(len(drums), "drums:", {v: sum(1 for d in drums if d[2] == v) for v in ("blue", "red", "rust", "cold")}, flush=True)

cut = {}
counts = [0] * len(drums)
for zone in ZONES:
    path = os.path.join(ROOT, "Assets", "models", "maps", "riverside", zone + ".obj")
    with open(path, encoding="utf-8", newline="") as h:
        lines = h.readlines()
    verts = []
    for line in lines:
        if line.startswith("v "):
            a, b, c = map(float, line[2:].split()[:3])
            verts.append((c, a, b))
    verts = np.array(verts)
    current = None
    drop = set()
    for n, line in enumerate(lines):
        if line.startswith("usemtl"):
            current = line.split()[1]
        elif line.startswith("f ") and current in DRUM_PAINTS:
            q = verts[[int(t.split("/")[0]) - 1 for t in line.split()[1:]]]
            for k, (_, at, _) in enumerate(drums):
                r = np.hypot(q[:, 0] - at[0], q[:, 1] - at[1])
                if r.max() < 13.0 and q[:, 2].min() > at[2] - 0.5 and q[:, 2].max() < at[2] + 35.5:
                    drop.add(n)
                    counts[k] += len(line.split()) - 3
                    break
    # A usemtl left with no faces goes too.
    kept = []
    for n, line in enumerate(lines):
        if n not in drop:
            kept.append(line)
    out = []
    for n, line in enumerate(kept):
        if line.startswith("usemtl"):
            following = next((x for x in kept[n + 1 :] if x.startswith(("f ", "usemtl"))), "")
            if not following.startswith("f "):
                continue
        out.append(line)
    cut[path] = (out, len(drop))
    print(zone, "faces to cut:", len(drop), flush=True)

for (name, _, variant), count in zip(drums, counts):
    want = EXPECTED[variant != "cold"]
    if count not in (0, want):
        raise SystemExit(f"{name} ({variant}) has {count} triangles to cut, not {want}: nothing written.")
if len(set(counts)) > 2 or (0 in counts and sum(counts)):
    raise SystemExit(f"Some drums were already cut and others not: {counts}. Nothing written.")

for path, (out, dropped) in cut.items():
    if dropped:
        with open(path, "w", encoding="utf-8", newline="") as h:
            h.writelines(out)

scene_file = M.SCENE_FILE
scene = json.loads(open(scene_file, encoding="utf-8").read())
objects = scene["GameObjects"]
group = K.game_object(M.ids, "Burn Drums", "drums", children=M.burn_drum_objects())
names = [o.get("Name") for o in objects]
if "Burn Drums" in names:
    objects[names.index("Burn Drums")] = group
else:
    objects.insert(names.index("Fires") + 1, group)
K.write_text(scene_file, json.dumps(scene, indent=2), newline=None)
print("triangles cut:", sum(counts), "scene:", len(group["Children"]), "burn drums", flush=True)
