"""Preserve the authored Fleet before the scoped discarded-tyre replacement."""
import hashlib
import json
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[3]
before = Path(__file__).parent / "tyres-before"
paths = ["Tools/lowtide_map.py", "Assets/scenes/maps/Lowtide/lowtide.scene"]
paths += ["Assets/models/maps/lowtide/lowtide_fleet" + suffix for suffix in
          (".obj", ".mtl", ".vmdl", "_hulls_dirt.obj", "_hulls_metal.obj")]
manifest = {}
for relative in paths:
    source, destination = root / relative, before / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        assert source.read_bytes() == destination.read_bytes(), relative
    else:
        shutil.copyfile(source, destination)
    manifest[relative] = hashlib.sha256(source.read_bytes()).hexdigest()
(before / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(f"Preserved {len(manifest)} source files")
