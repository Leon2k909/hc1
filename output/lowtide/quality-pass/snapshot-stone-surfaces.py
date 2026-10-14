"""Preserve current materials and hash geometry before the stone-surface pass."""
import hashlib
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
folder = Path(__file__).parent / "stone-surfaces-before"
sources = ["Tools/lowtide_banks.py", "Assets/shaders/hc1_lowtide_stone.shader",
           "Assets/materials/lowtide/marine/lt_tidal_granite.vmat",
           "Assets/materials/lowtide/marine/lt_tidal_brick.vmat"]
manifest = {"sources": {}, "geometry_and_scene": {}}
for relative in sources:
    source, dest = ROOT / relative, folder / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        assert dest.read_bytes() == source.read_bytes(), relative
    else:
        shutil.copyfile(source, dest)
    manifest["sources"][relative] = hashlib.sha256(source.read_bytes()).hexdigest()
files = [ROOT / "Assets/scenes/maps/Lowtide/lowtide.scene"]
files += [p for p in (ROOT / "Assets/models/maps/lowtide").iterdir() if p.suffix in (".obj", ".mtl", ".vmdl")]
for p in files:
    manifest["geometry_and_scene"][p.relative_to(ROOT).as_posix()] = hashlib.sha256(p.read_bytes()).hexdigest()
(folder / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
print(f"Preserved {len(sources)} sources; hashed {len(files)} geometry/scene files")
