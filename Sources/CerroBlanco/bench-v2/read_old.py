# Make the old bench from the map's own code, only to render a fair "before". Nothing here is shipped, and no map file is touched.
#   python read_old.py <project root> <out dir>
import os
import pathlib
import sys

sys.dont_write_bytecode = True
ROOT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import cerroblanco_parts as P  # noqa: E402
import map_kit as K  # noqa: E402

model = K.Model()
# The map's plan is (east, north), and north is engine X, so this lies the old one the same way as the new one. 96 is its longest common length.
P.bench(model, 0.0, 0.0, length=96.0, along="n")
for paint in model.polygons:
    # What the map sets when it writes its models (cerroblanco_map.configure).
    model.tile_overrides[paint] = P.TILED.get(paint, 64.0)
target = pathlib.Path(OUT) / "old_bench.obj"
K.write_obj(target, model, "old_bench")
print("written", target, "paints", list(model.polygons))
