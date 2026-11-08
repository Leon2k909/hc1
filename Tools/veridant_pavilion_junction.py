"""Close the garden pavilion wall returns and carry the floor through its doors."""
from pathlib import Path
import map_kit as K
import veridant_map as V

resource = 'models/maps/veridant/pavilion-junction'
model = K.Model()
model.uv_source_name = 'veridant_dress'
for n, facing in [(-1180, -1), (-940, 1)]:
    for start, end in [(120, 136), (304, 320)]:
        V.card(model, 'vr_stone', [V.v(start,n,0), V.v(end,n,0),
                                  V.v(end,n,140), V.v(start,n,140)], V.v(0,facing,0))
for start, end in [(-1180, -1164), (-956, -940)]:
    V.floor(model, 175, 265, start, end, .2, 'vr_floor')
V.configure(model)
K.write_model(Path(__file__).resolve().parents[1] / 'Assets' / resource,
              resource, 'junction', model)
