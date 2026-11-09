"""Proves Tools/boxyard_map.py writes the yard model exactly as it is installed (the floor on the v2 concrete).

    python Sources/Boxyard/yard-concrete-v2/verify_generator.py

Builds the generator's models in memory, writes only the yard model into a temporary folder and compares its files
byte for byte with Assets/models/maps/boxyard/.  Nothing in the project is written."""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
os.chdir(ROOT)

import boxyard_map as B  # noqa: E402
import map_kit as K      # noqa: E402

models, _, _ = B.build()
installed = ROOT / "Assets" / "models" / "maps" / "boxyard"
bad = 0
with tempfile.TemporaryDirectory() as tmp:
    K.write_model(Path(tmp), B.RESOURCE_DIR, "boxyard_yard", models["boxyard_yard"])
    for path in sorted(Path(tmp).iterdir()):
        there = installed / path.name
        same = there.exists() and there.read_bytes() == path.read_bytes()
        bad += not same
        print(("same     " if same else "DIFFERENT"), path.name)
remap = [line.strip() for line in (installed / "boxyard_yard.vmdl").read_text().splitlines() if "bx_concrete.vmat" in line]
print(remap)
sys.exit(1 if bad or B.YARD_CONCRETE not in remap[0] else 0)
