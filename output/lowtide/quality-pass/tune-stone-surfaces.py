import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT / "Tools"))
import lowtide_banks as B

folder = Path(__file__).parent
manifest = {}
for relative,source in B.stone_material_sources().items():
    current = ROOT / "Assets" / relative
    stage = folder / "stone-surfaces-stage/Assets" / relative
    assert current.read_bytes()==stage.read_bytes(), relative
    manifest[relative] = hashlib.sha256(current.read_bytes()).hexdigest()
    stage.write_text(source)
(folder / "stone-surface-tune-input.json").write_text(json.dumps(manifest,indent=2)+"\n")
print("Staged final stone tints")
