# Write today's IBC tote out with the map's own generator, only to render a fair "before". Nothing here is shipped.
#   python read_old.py <project root> <out dir>
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, "Tools"))
os.chdir(root)
import boxyard_map as B  # noqa: E402
import map_kit as K  # noqa: E402

os.makedirs(out, exist_ok=True)
model = K.Model()
B.ibc(model, 0.0, 0.0, 0.0)
B.configure(model)
print(K.write_model(Path(out), "unused", "old_ibc", model), "triangles", model.bounds())
