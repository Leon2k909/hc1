"""Rewrite the installed stair rear closures from ares_stair_cladding.py. Never touches the shared hall.

The first install's end caps lay exactly on the stair walls and z-fought all up both corners of all four stairs. Keeps a
copy of what it replaces in output/ares/stair-rear-wall/before-zfight-fix/. Compile the VMDL afterwards.
"""
import filecmp
from pathlib import Path
import shutil

import ares_map as A
import map_kit as K
from ares_stair_cladding import append_rear_closure

ROOT = Path(__file__).resolve().parents[1]
NAME = "ares_stair_rear_closures"
RESOURCE = "models/maps/ares/stair-rear-wall"
INSTALLED = ROOT / "Assets" / RESOURCE
OUT = ROOT / "output/ares/stair-rear-wall"


def main():
    model = K.Model()
    for across, run in ((A.STAIR_E, A.STAIR_N), (A.WING_STAIR_E, A.WING_STAIR_N)):
        for sign in (-1, 1):
            c0, c1 = sorted((sign * across[0], sign * across[1]))
            append_rear_closure(model, "n", c0, c1, *run, 0, A.G, A.DT)
    assert not model.boxes and not model.hulls
    A.configure(model)

    stage = OUT / "stage-zfight-fix"
    stage.mkdir(parents=True, exist_ok=True)
    K.write_obj(stage / (NAME + ".obj"), model, NAME)
    K.write_vmdl(stage / (NAME + ".vmdl"), RESOURCE, NAME, model)
    assert filecmp.cmp(stage / (NAME + ".vmdl"), INSTALLED / (NAME + ".vmdl"), shallow=False), "the model doc itself should not change"

    keep = OUT / "before-zfight-fix"
    keep.mkdir(exist_ok=True)
    backup = keep / (NAME + ".obj")
    if not backup.exists():
        shutil.copy2(INSTALLED / (NAME + ".obj"), backup)
    shutil.copy2(stage / (NAME + ".obj"), INSTALLED / (NAME + ".obj"))
    print("closures rewritten:", model.triangle_count(), "triangles; the old OBJ is in", backup)


if __name__ == "__main__":
    main()
