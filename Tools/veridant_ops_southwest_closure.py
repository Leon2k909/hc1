"""Close the exposed Operations southwest corner and slab edge."""
from pathlib import Path
import map_kit as K
import veridant_map as V

resource = 'models/maps/veridant/ops-southwest-closure'
model = K.Model()
model.uv_source_name = 'veridant_buildings'

# Close only the open wall thickness and exposed slab band.
for n0,n1,z0,z1 in [(-700,-684,0,112), (-700,-560,112,128)]:
    V.card(model, 'vr_stone', [V.v(-200,n0,z0), V.v(-200,n1,z0),
                              V.v(-200,n1,z1), V.v(-200,n0,z1)], V.v(-1,0,0))
V.card(model, 'vr_stone', [V.v(-200,-700,112), V.v(760,-700,112),
                          V.v(760,-700,128), V.v(-200,-700,128)], V.v(0,-1,0))
V.configure(model)
K.write_model(Path(__file__).resolve().parents[1] / 'Assets' / resource,
              resource, 'closure', model)
