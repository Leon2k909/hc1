"""Prepare/install only Riverside's four chair replacements, without regenerating its map.

python install_chairs.py <root> <exchange-directory> [--apply]
Mesh cuts retain all other lines and collision files. The scene is saved separately by the editor.
"""
import json
import math
from pathlib import Path
import shutil
import sys

import numpy as np

sys.dont_write_bytecode = True
ROOT = Path(sys.argv[1]).resolve()
EXCHANGE = Path(sys.argv[2])
APPLY = "--apply" in sys.argv
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverside_map as M
import riverside_parts as P

P.reset()
zones = {name: K.Model() for name in ("riverside_low", "riverside_terrace", "riverside_levee", "riverside_dressing")}
M.trailers(zones["riverside_low"], zones["riverside_terrace"], zones["riverside_levee"])
# The dressing's sole chair, using its authored placement without regenerating the dressing.
P.lawn_chair(zones["riverside_dressing"], (-420, 1060), (0.7, 0.7))
file_of = {id(model): name for name, model in zones.items()}
spots = [dict(zone=file_of[id(owner)], position=list(K.to_world(position)),
              yaw=K.plan_yaw((math.cos(math.radians(yaw)), math.sin(math.radians(yaw)))) % 360,
              colour=colour) for owner, position, yaw, colour in P.LAWN_CHAIRS]
assert len(spots) == 4 and [s["colour"] for s in spots].count("red") == 1, spots
group = K.game_object(M.ids, "Lawn Chairs", "lawn_chairs", children=M.lawn_chair_objects())
EXCHANGE.mkdir(parents=True, exist_ok=True)
(EXCHANGE / "chair-placements.json").write_text(json.dumps(dict(spots=spots, group=group), indent=2))
template = (Path(__file__).parent / "install-editor.cs.txt").read_text()
(EXCHANGE / "install-chairs.cs").write_text(template.replace("%PLAN_PATH%", (EXCHANGE / "chair-placements.json").as_posix()))
shutil.copyfile(Path(__file__).parent / "check-installed.cs.txt", EXCHANGE / "check-chairs.cs")
print(json.dumps(spots, indent=2))

prepared = []
for name in sorted({s["zone"] for s in spots}):
    path = ROOT / "Assets/models/maps/riverside" / (name + ".obj")
    original = path.read_bytes()
    lines = original.decode("utf-8").splitlines(keepends=True)
    # The generator's OBJ axes are (engine Y, engine Z, engine X).
    vertices = np.array([(float(p[2]), float(p[0]), float(p[1]))
                         for line in lines if line.startswith("v ") for p in [line.split()[1:4]]])
    local_spots = [s for s in spots if s["zone"] == name]
    counts = [0] * len(local_spots)
    cut = set()
    material = None
    for i, line in enumerate(lines):
        if line.startswith("usemtl "):
            material = line.split()[1]
        elif line.startswith("f "):
            points = vertices[[int(t.split("/")[0]) - 1 for t in line.split()[1:]]]
            for k, spot in enumerate(local_spots):
                if material not in ("rs_alu", "rs_drum_red" if spot["colour"] == "red" else "rs_lawn_chair"):
                    continue
                delta = points - np.asarray(spot["position"])
                a = math.radians(spot["yaw"])
                forward = delta[:, 0] * math.cos(a) + delta[:, 1] * math.sin(a)
                side = -delta[:, 0] * math.sin(a) + delta[:, 1] * math.cos(a)
                if (forward.min() >= -12.6 and forward.max() <= 8.6 and abs(side).max() <= 10.6
                        and delta[:, 2].min() >= -0.6 and delta[:, 2].max() <= 34.6):
                    cut.add(i)
                    counts[k] += 1
                    break
    print(name, "old chair faces", counts)
    # 6 open five-sided tubes (10 triangles each) plus the 8 double-sided card triangles.
    assert all(c in (0, 68) for c in counts), (name, counts)
    assert len(set(counts)) == 1, (name, counts)
    if cut:
        prepared.append((path, original, "".join(line for i, line in enumerate(lines) if i not in cut).encode("utf-8")))

if APPLY:
    backup = ROOT / "output/asset-improvement-20261030/lawn-chair/before-install"
    backup.mkdir(parents=True, exist_ok=True)
    for path, original, replacement in prepared:
        assert path.read_bytes() == original, f"Changed during preparation: {path}"
        if not (backup / path.name).exists():
            shutil.copy2(path, backup / path.name)
        incoming = path.with_suffix(path.suffix + ".chairs-incoming")
        incoming.write_bytes(replacement)
        incoming.replace(path)
        print("Cut old chairs:", path.name)
else:
    print("Dry run; pass --apply to cut the old meshes. Scene placement data is in", EXCHANGE)
