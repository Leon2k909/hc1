"""Woven rug surface and bound border for the gallery seating group."""
import numpy as np
def build_into(m,c=(0,0),z0=0):
    def panel(a,b,d,e,paint):
        pts=[np.array((c[0]+x,c[1]+y,z0+.12)) for x,y in [(a,d),(b,d),(b,e),(a,e)]]
        m.polygon(paint,pts,normal=np.array((0,0,1.)),uv=[((p[0]-c[0])/24,(p[1]-c[1])/24) for p in pts])
    panel(-167,167,-117,117,'vr_gallery_rug_generated')
    for a,b,d,e in [(-170,-167,-120,120),(167,170,-120,120),(-167,167,-120,-117),(-167,167,117,120)]:
        panel(a,b,d,e,'vr_gallery_rug_binding')
    m.material_overrides['vr_gallery_rug_generated']='materials/veridant/gallery-rug-v3/generated.vmat'
    m.material_overrides['vr_gallery_rug_binding']='materials/veridant/gallery-rug-v1/binding.vmat'
    for paint in m.material_overrides:m.tile_overrides[paint]=24
