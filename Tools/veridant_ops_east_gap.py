"""Close the operations east threshold and the exposed garden wall end."""
from pathlib import Path
import map_kit as K
import veridant_map as V

resource = 'models/maps/veridant/ops-east-gap-fix'
model = K.Model()
model.uv_source_name = 'veridant_buildings'
V.floor(model, 744, 760, -640, -560, 0, 'vr_floor')
V.card(model, 'vr_stone', [V.v(760, -700, 0), V.v(760, -684, 0),
                          V.v(760, -684, 112), V.v(760, -700, 112)], V.v(1, 0, 0))
V.configure(model)
K.write_model(Path(__file__).resolve().parents[1] / 'Assets' / resource,
              resource, 'ops_east_gap_fix', model)
