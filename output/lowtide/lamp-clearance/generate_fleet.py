"""Stage just Lowtide's updated Fleet render mesh without rebuilding other assets."""
import hashlib
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))

import map_kit as K
import lowtide_map as M

dest = Path(__file__).parent / "stage" / "lowtide_fleet.obj"
dest.parent.mkdir(parents=True, exist_ok=True)
model = M.fleet()
M.MARINE.strip_model(model)
M.configure(model)
triangles = K.write_obj(dest, model, "lowtide_fleet")
placements = M.LANTERNS.placements()
assert triangles == 77814, triangles
assert len(model.boxes) == 25 and len(model.hulls) == 22
assert [(e, n) for e, n, _ in placements] == [
    (-240, 1167), (-240, 1433), (240, 1167), (240, 1433)
], placements
clearance = min(1167 - 10.15 - M.STREET_N[0], M.STREET_N[1] - 1433 - 10.15)
assert clearance > 6, clearance
print("Fleet triangle count", triangles)
print("Lantern placements", placements)
print("Roof-wall clearance", clearance)
print("Old SHA256", hashlib.sha256((M.OUT_DIR / "lowtide_fleet.obj").read_bytes()).hexdigest())
print("New SHA256", hashlib.sha256(dest.read_bytes()).hexdigest())
print("Staged mesh", dest)
