"""Verify the bank materials' compiled texture references resolve on disk."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[3]
ASSETS = ROOT / "Assets"
ENGINE = Path("D:/SteamLibrary/steamapps/common/sbox")
folder = Path(__file__).parent
materials = json.loads((folder / "banks-stage/materials.json").read_text())
report = {}
for relative, source in materials.items():
    path = ASSETS / relative
    assert path.read_text() == source, relative
    compiled = path.with_suffix(".vmat_c")
    references = sorted(set(x.decode() for x in re.findall(rb"materials/[a-zA-Z0-9_./-]+[.]vtex", compiled.read_bytes())))
    assert references, relative
    dependencies = {ref: any((root / (ref + "_c")).is_file() for root in (ASSETS, ENGINE / "core")) for ref in references}
    assert all(dependencies.values()), dependencies
    report[relative] = dependencies
for name in ("hc1_lowtide_stone", "hc1_lowtide_silt"):
    assert (ASSETS / "shaders" / (name + ".shader_c")).is_file()
(folder / "bank-material-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
