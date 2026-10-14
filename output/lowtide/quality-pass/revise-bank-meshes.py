"""Stage a bank-shape revision against the successfully applied first pass."""
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_marine as M
import lowtide_finish as F

folder = Path(__file__).parent
stage = folder / "banks-stage"
replaces = {}
for name in (M.NAME, F.MODEL):
    for ext in (".obj", ".mtl", ".vmdl"):
        current = L.OUT_DIR / (name + ext)
        assert current.read_bytes() == (stage / current.name).read_bytes(), f"Concurrent change: {current.name}"
        replaces[current.name] = hashlib.sha256(current.read_bytes()).hexdigest()
(stage / "revision-replaces.json").write_text(json.dumps(replaces, indent=2) + "\n")
manifest = json.loads((stage / "manifest.json").read_text())
for module, name in ((M, M.NAME), (F, F.MODEL)):
    model = module.build(L)
    assert not model.boxes and not model.hulls and not model.props
    count = K.write_model(stage, L.RESOURCE_DIR, name, model)
    manifest[name]["triangles"] = count
    print(name, count)
(stage / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
