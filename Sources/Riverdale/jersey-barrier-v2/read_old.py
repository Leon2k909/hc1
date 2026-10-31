# Make the old barrier from the map's own code, only to render a fair "before". Nothing here is shipped, and no map file is touched.
#   python read_old.py <project root> <out dir>
import os
import pathlib
import sys

sys.dont_write_bytecode = True
ROOT, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
sys.path.insert(0, os.path.join(ROOT, "Tools"))
import map_kit as K  # noqa: E402
import riverdale_parts as P  # noqa: E402

model = K.Model()
# The map's plan is (east, north), and north is engine X, so this lies the old one the same way as the new one.
P.jersey(model, (0.0, 0.0), (0.0, 1.0))
# The map sets each paint's tile when it writes its models, 64 inches for this one (riverdale_map.py).
model.tile_overrides["rv_precast"] = 64.0
target =pathlib.Path(OUT) / "old_barrier.obj"
K.write_obj(target, model, "old_barrier")
print("written", target)
