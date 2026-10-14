"""Stage surface maps, materials and shader without rebuilding map geometry."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import uuid

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT / "Tools"))
import lowtide_banks as B

folder = Path(__file__).parent
before = json.loads((folder / "stone-surfaces-before/manifest.json").read_text())
for relative,expected in before["sources"].items():
    if relative.startswith("Assets/"):
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()==expected,relative
stage = folder / "stone-surfaces-stage/Assets"
B.bake_stone_surfaces(stage / B.STONE_RESOURCE)
for relative,source in B.stone_material_sources().items():
    (stage / relative).write_text(source)
shader = stage / "shaders/hc1_lowtide_stone.shader"
shader.parent.mkdir(parents=True,exist_ok=True)
shutil.copyfile(folder / "stone-surface.shader",shader)
for path in stage.rglob("*"):
    if path.is_file() and path.suffix!=".meta":
        relative = path.relative_to(stage)
        meta = ROOT / "Assets" / Path(str(relative)+".meta")
        dest = Path(str(path)+".meta")
        if meta.exists():
            shutil.copyfile(meta,dest)
        else:
            dest.write_text(json.dumps({"guid":str(uuid.uuid5(uuid.NAMESPACE_URL,relative.as_posix()))},indent=2)+"\n")
print(f"Staged {len(list(stage.rglob('*.png')))} maps, two materials and one shader")
