from pathlib import Path
import datetime
import json

root = Path("Assets/models/maps/lowtide")
stage = Path("output/lowtide/quality-pass/banks-stage")
for name in ("lowtide_marine", "lowtide_finish"):
    source = root / (name + ".obj")
    compiled = root / (name + ".vmdl_c")
    print(name, "staged source present:", source.read_bytes() == (stage / source.name).read_bytes(),
          "compiled:", datetime.datetime.fromtimestamp(compiled.stat().st_mtime).isoformat())
for relative, source in json.loads((stage / "materials.json").read_text()).items():
    path = Path("Assets") / relative
    print(relative, "staged source present:", path.exists() and path.read_text() == source)
log = Path("D:/SteamLibrary/steamapps/common/sbox/logs/sbox-dev.log").read_text(errors="replace").splitlines()
print("Recent engine messages:")
print("\n".join(log[-35:]))
