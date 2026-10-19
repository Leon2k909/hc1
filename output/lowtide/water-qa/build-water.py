"""Scoped Lowtide water rebuild. Leave all other scene and model files untouched."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L

model = L.water_model()
L.configure(model)
surfaces = model.polygons["lt_water"]
assert len(surfaces) > 2, "Puddles and both main surfaces are expected"
canal, *sea = surfaces[:4]
for polygon in (canal, *sea):
    assert all(abs(p[2] - L.WATER_Z) < 0.001 for p in polygon[0])
assert all(L.MOUTH_N == float(p[0][2][1]) for p in sea)
assert float(canal[0][0][1]) == L.MOUTH_N
assert not model.boxes and not model.hulls

count = K.write_model(L.OUT_DIR, L.RESOURCE_DIR, "lowtide_water", model)
print(f"Lowtide water: {count} render triangles, {len(surfaces)} surfaces, ")
print(f"Canal and sea at z={L.WATER_Z}, edge n={L.MOUTH_N}, no sloping connector")
