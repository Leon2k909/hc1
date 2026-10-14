"""Check architectural mask registration, material scope and resource integrity."""
import json
from pathlib import Path
import sys

import numpy as np
from PIL import Image

FOLDER = Path(__file__).resolve().parent
ROOT = FOLDER.parents[2]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_brick as B
import lowtide_facade as F
import lowtide_map as L

data = json.loads((FOLDER / "facade-layout.json").read_text())
assert data["openings"] == F.layout(L), "Mask layout differs from the canonical warehouse"
pixels = np.asarray(Image.open(ROOT / "Assets" / F.RESOURCE))
assert pixels.shape == (2048, 4096, 3)
below, above = [], []
for side in range(2):
    for record in data["openings"]:
        c = record["cell"]
        start, end = L.SPEICHER[2:] if c < 2 else L.SPEICHER[:2]
        x = round(F.PAD + ((record["r0"]+record["r1"])/2-start)/(end-start)*(F.CELL-2*F.PAD-1))
        for offset, readings in ((-1, below), (6, above)):
            z = record["sill"]+offset
            y = round(F.PAD + (1-z/1024)*(F.CELL-2*F.PAD-1))
            readings.append(int(pixels[side*F.CELL+y, c*F.CELL+x, 0]))
assert min(below) > 75, "A contact mask misses its sill"
assert max(above) < 15, "Contact shading leaked into a window opening"
assert not np.array_equal(pixels[:1024, :, 1], pixels[1024:, :, 1]), "Both warehouses have identical runoff"
for name in ("lt_brick", "lt_brick_soot"):
    path = ROOT / "Assets/materials/lowtide" / (name + ".vmat")
    assert path.read_text() == B.material_text(*B.VARIANTS[name], facade=True)
    before = (FOLDER / "facade-before" / path.name).read_text()
    properties = '    TextureFacadeWear "materials/lowtide/masonry/facade_wear.png"\n    g_flFacadeWear "1"\n'
    assert path.read_text().replace(properties, "") == before
for name in ("lt_brick_glazed", "lt_brick_slime"):
    assert "g_flFacadeWear" not in (ROOT / "Assets/materials/lowtide" / (name+".vmat")).read_text()
dependencies = json.loads((FOLDER / "facade-material-dependencies.json").read_text())
assert len(dependencies) == 8 and all(refs and all(refs.values()) for refs in dependencies.values())
report = {
    "registered_sills": len(below), "minimum_contact_under_sill": min(below),
    "maximum_contact_above_sill": max(above), "different_runoff_per_building": True,
    "only_two_base_materials_opt_in": True, "generator_matches_materials": True,
    "all_eight_shared_shader_material_dependencies_resolve": True,
}
(FOLDER / "facade-checks.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report, indent=2))
