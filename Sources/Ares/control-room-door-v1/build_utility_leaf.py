"""A human-scale single sliding utility leaf, in inches. Stage before native import."""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as P

AXES=((1,0,0),(0,1,0),(0,0,1))
m=K.Model()
def box(c,size,paint,bevel=.12):
    P.bevel_box(m,c,AXES,size,paint,bevel=bevel)

# A thin folded steel shell, with a shallow central pressing on both faces.
box((0,0,0),(65,3,98),'paint',.22)
for side in (-1,1):
    box((0,side*1.53,7),(55,.08,72),'gasket',.03)
    box((0,side*1.59,7),(54.55,.10,71.55),'paint',.04)
    # A plain low kick strip and a compact recessed finger pull at the closing edge.
    box((0,side*1.66,-38),(56,.22,13),'metal',.09)
    box((25,side*1.62,0),(3.5,.18,11),'metal',.08)
    box((25,side*1.74,0),(2.5,.12,9.8),'gasket',.05)
    box((25.75,side*1.86,0),(.45,.22,8.4),'alloy',.08)
    for z in (-5,5):
        box((25,side*1.75,z),(.35,.15,.35),'alloy',.05)

m.material_overrides.update({
 'paint':'materials/ares/pressure-doors-v3/body.vmat',
 'gasket':'materials/ares/ar_rubber.vmat',
 'metal':'materials/ares/ar_gunmetal.vmat',
 'alloy':'materials/collider/co_silver.vmat',
})
for name in m.material_overrides:m.tile_overrides[name]=32
out=Path(__file__).parent/'stage'
count=K.write_model(out,'models/maps/ares/control-room-door-v1','utility_leaf',m)
print(f'Staged utility leaf: {count} triangles, four materials, 65 x 98 inches')
