"""Snapshot the current scene and geometry before the native lighting integration."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent / "warehouse-lighting-before"
OUT.mkdir(exist_ok=True)
scene = ROOT / "Assets/scenes/maps/Lowtide/lowtide.scene"
if (OUT / "lowtide.scene").exists():
    raise SystemExit("Lighting baseline already exists; inspect before replacing it")
(OUT / "lowtide.scene").write_bytes(scene.read_bytes())
paths = sorted((ROOT / "Assets/models/maps/lowtide").glob("*"))
paths = [p for p in paths if p.suffix.lower() in {".obj", ".vmdl", ".fbx"}]
hashes = {str(p.relative_to(ROOT)).replace("\\", "/"): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
hashes[str(scene.relative_to(ROOT)).replace("\\", "/")] = hashlib.sha256(scene.read_bytes()).hexdigest()
(OUT / "manifest.json").write_text(json.dumps(hashes, indent=2) + "\n")
print(f"Snapshot saved: {len(paths)} geometry files and the current Lowtide scene")
