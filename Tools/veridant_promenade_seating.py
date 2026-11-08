"""Fit teak seating beside the promenade planters, clear of the spawn rows."""
from pathlib import Path
import map_kit as K
import veridant_map as V
from veridant_bench import build_into

resource = 'models/maps/veridant/promenade-planter-seating'
model = K.Model()
for e, n, offsets in [(-1100, -150, (-51, 51)), (-1100, 250, (-51, 51)),
                      (-1300, -1150, (51,))]:
    for offset in offsets:
        build_into(model, (e, n + offset), (1, 0), 72)
V.configure(model)
K.write_model(Path(__file__).resolve().parents[1] / 'Assets' / resource,
              resource, 'seating', model)
