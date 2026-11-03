"""Check that installation only added the chairs and removed their 272 old triangles."""
import json
from pathlib import Path
import sys

ROOT = Path(sys.argv[1]).resolve()
BACKUP = ROOT / "output/asset-improvement-20261030/lawn-chair/before-install"
scene = json.loads((ROOT / "Assets/scenes/maps/Riverside/riverside.scene").read_text())
before = json.loads((BACKUP / "riverside.scene").read_text())
group = next(g for g in scene["GameObjects"] if g.get("Name") == "Lawn Chairs")
assert len(group["Children"]) == 4
models = [c["Components"][0]["Model"] for c in group["Children"]]
models = [m["Path"] if isinstance(m, dict) else m for m in models]
assert sum(p.endswith("green.vmdl") for p in models) == 3
assert sum(p.endswith("red.vmdl") for p in models) == 1
scene["GameObjects"].remove(group)

def check_existing(a, b):
    if isinstance(a, dict):
        # SceneFile.Load applies the engine's component-version upgrade on save.
        allowed = {"__version"}
        if a.get("__type") == "Sandbox.EnvmapProbe" and a.get("RenderDynamically") is True:
            allowed.add("Mode")
            assert b.get("Mode") == "Realtime"
        assert set(b) - set(a) <= allowed, (set(a), set(b))
        if "__version" not in a and "__version" in b:
            assert b["__version"] == 1
        for key in a:
            check_existing(a[key], b[key])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            check_existing(x, y)
    else:
        assert a == b, (a, b)

check_existing(before, scene)
for name, count in (("riverside_dressing.obj", 68), ("riverside_levee.obj", 68), ("riverside_terrace.obj", 136)):
    old = (BACKUP / name).read_bytes().splitlines(keepends=True)
    new = (ROOT / "Assets/models/maps/riverside" / name).read_bytes().splitlines(keepends=True)
    # Only complete face lines were removed; every other byte and retained face remains in order.
    j = 0
    dropped = []
    for line in old:
        if j < len(new) and line == new[j]:
            j += 1
        else:
            dropped.append(line)
    assert j == len(new) and len(dropped) == count and all(line.startswith(b"f ") for line in dropped)
    print(name, "only old chair triangles removed:", count)
print("PASS: four chairs (3 green, 1 red); existing scene content unchanged apart from engine component upgrades.")
