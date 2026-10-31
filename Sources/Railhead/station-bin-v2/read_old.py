# Make the old bin from the map's own code, only to render a fair "before". Nothing here is shipped, and no map file is touched.
#   python read_old.py <project root> <out dir>
import os
import pathlib
import sys

sys.dont_write_bytecode = True
ROOT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import railhead_buffer as RB  # noqa: E402
import railhead_furniture as FU  # noqa: E402
import railhead_materials as RM  # noqa: E402
import railhead_props as P  # noqa: E402

model = K.Model()
# The map's plan is (east, north), and north is engine X, so its front faces engine +X, the way the new one is built.
FU.bin(model, P.frame_for(0.0, 0.0, 0.0, "+n"))
# What the map sets when it writes its models (railhead_map), so the old surfaces tile as they do in the game.
known = RM.paints()
tiles = getattr(RB, "RW_TILES", {})
for paint in model.polygons:
    model.tile_overrides[paint] = float((known[paint][1] if paint in known else tiles.get(paint)) or 64.0)
print("tiles", dict(model.tile_overrides))
target = pathlib.Path(OUT) / "old_bin.obj"
K.write_obj(target, model, "old_bin")
print("written", target, "paints", list(model.polygons))
