"""Close the exposed Operations east wall end and floor slab edge."""
from pathlib import Path

import map_kit as K
import veridant_map as V

resource = "models/maps/veridant/ops-east-slab-closure"
model = K.Model()
model.uv_source_name = "veridant_buildings"

_, east, south, _ = V.OPS
V.floor(model, east - V.T, east, -640, -560, 0, "vr_floor")

# The slab has collision already. Its lobby section was built without side faces.
for start, end, bottom, top in (
    (south, south + V.T, 0, 112),
    (south, V.OPS_FACE, 112, V.L1),
    (south, south + V.T, V.L1, V.OPS_TOP),
):
    V.card(
        model, "vr_stone",
        [V.v(east, start, bottom), V.v(east, end, bottom),
         V.v(east, end, top), V.v(east, start, top)],
        V.v(1, 0, 0),
    )

V.configure(model)
K.write_model(Path(__file__).resolve().parents[1] / "Assets" / resource,
              resource, "closure", model)
