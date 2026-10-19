"""Rebuild numerical contact fields against the installed grates/construction."""
import json
import sys
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_paving_use as U
import numpy as np
from PIL import Image

BASE = Path(__file__).resolve().parent
STAGE = BASE / "stage"
assert not (BASE / "manifest.json").exists(), "Preserve the previous staging record"
construction = json.loads((ROOT / "Sources/Lowtide/construction/recomposed-status.json").read_text())
assert construction["native_accepted"] and construction["canonical_generator_integrated"]
for name, expected in construction["installed_files"].items():
    assert U.sha(ROOT / name) == expected, name
ground, segments, sources = U.saved_surfaces()
settings = json.loads((U.SOURCE / "edge-use.json").read_text())
outlets = U.current_drain_outlets()
assert len(outlets) == 36
historical = U.drain_outlets()
assert all(a["kind"] == b["kind"] and np.allclose(a["position"], b["position"], atol=1e-10) for a, b in zip(outlets, historical))
data, _ = U.fields(ground, segments, outlets, settings)
(STAGE / U.MASK).parent.mkdir(parents=True, exist_ok=True)
Image.fromarray(data).save(STAGE / U.MASK)
U.write(STAGE / U.SHADER, U.shader())
material = U.contact_material((U.ASSETS / U.MATERIAL).read_text(), settings)
U.write(STAGE / U.MATERIAL, material)
for rel in (U.MASK, U.SHADER):
    U.write(Path(str(STAGE / rel) + ".meta"), json.dumps(dict(guid=str(uuid.uuid5(uuid.NAMESPACE_URL, rel))), indent=2) + "\n")
for path in (U.BASE_SHADER, U.ASSETS / U.MATERIAL, U.SOURCE / "edge-use.json", U.SOURCE / "edge-use.hlsl", ROOT / "Assets/scenes/maps/Lowtide/lowtide.scene"):
    sources[path.relative_to(ROOT).as_posix()] = U.sha(path)
files = {p.relative_to(STAGE).as_posix(): U.sha(p) for p in STAGE.rglob('*') if p.is_file()}
assert all(U.sha(ROOT / p) == h for p, h in sources.items())
manifest = dict(status="native_review_pending", sources=sources, staged_files=files,
    live_before={p: U.sha(U.ASSETS / p) if (U.ASSETS / p).exists() else None for p in files},
    ground_triangles=len(ground), wall_segments=len(segments), outlets=outlets,
    drains_over_setts=sum(d["domain_samples"] > 0 for d in outlets),
    new_geometry=0, new_material_slots=0, extra_texture_lookups=1,
    construction="Sources/Lowtide/construction/recomposed-status.json",
    production_changed=False, settings=settings)
U.write(BASE / "manifest.json", json.dumps(manifest, indent=2) + "\n")
print(json.dumps({k: manifest[k] for k in ["ground_triangles", "wall_segments", "drains_over_setts", "new_geometry", "new_material_slots"]}))
