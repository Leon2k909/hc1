# Write today's red crate out with the map's own generator, only to render a fair "before". Nothing here is shipped.
#   python read_old.py <project root> <out dir>
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True
root, out = sys.argv[1], sys.argv[2]
sys.path.insert(0, os.path.join(root, "Tools"))
os.chdir(root)
import map_kit as K  # noqa: E402
import orion_map as B  # noqa: E402
import orion_parts as OP  # noqa: E402

os.makedirs(out, exist_ok=True)
model = K.Model()
OP.red_crate(model, (0.0, 0.0), (1, 0), (44, 34, 40))
B.configure(model)
print(K.write_model(Path(out), "unused", "old_red_crate", model), "triangles", model.bounds())
