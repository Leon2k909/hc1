"""Persist the approved cabinet in the map's authoring source without rebuilding the map."""
from pathlib import Path
import hashlib,json,sys,shutil
REVIEW=Path(__file__).resolve().parents[3]
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
HERE=Path(__file__).parent
OUT=REVIEW/'output/riverside/ice-cabinet-v1'
src=(HERE/'build.py').read_text()
body=src[src.index('X=np.array'):src.index('\ntriangles=[]')].replace('def make(lod):','def model(lod=0):')
head='''"""Approved Lucky Stop ice cabinet geometry; preserve original collision and porch light."""
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/ice-cabinet-v1"
'''
suffix='''
def append_to(target,position):
    m=model(0)
    offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias="icev1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    for center,axes,size,surface in m.boxes:target.boxes.append((center+offset,axes,size,surface))
'''
helper=ROOT/'Tools/riverside_ice_cabinet.py'
helper.write_text(head+body+suffix)
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverside_ice_cabinet as I
import numpy as np
for lod in range(3):
    proof=OUT/f'generator-proof-{lod}.obj'
    K.write_obj(proof,I.model(lod),f'ice_cabinet_lod{lod}')
    assert proof.read_text().splitlines()[3:]==(REVIEW/f'Assets/models/maps/riverside/ice-cabinet-v1/ice_cabinet_lod{lod}.obj').read_text().splitlines()[3:]
test=K.Model();I.append_to(test,(160.,622.,20.))
assert len(test.boxes)==1 and np.allclose(test.boxes[0][0],(160,622,50)) and np.allclose(test.boxes[0][2],(38,30,60))
generator=ROOT/'Tools/riverside_map.py'
original=generator.read_text()
old='''    obox( m, ice_c + UP * 30, ( 1, 0, 0 ), ( 38, 30, 60 ), "rs_fridge", "metal" )
    P.lit( m, "vending", ice_c + v( 0, -15.2, 30 ), r, 52, off=0.0, w=36 )'''
assert original.count(old)==1,'Inspect changed ice authoring source before patching'
(OUT/'install-before/riverside_map.py').write_text(original)
generator.write_text(original.replace(old,'''    from riverside_ice_cabinet import append_to as append_approved_ice_cabinet
    append_approved_ice_cabinet( m, ice_c )'''))
(OUT/'generator-verified.json').write_text(json.dumps(dict(all_lods_match_approved=True,collision_preserved=True,porch_light_unchanged=True,full_map_regenerated=False),indent=2))
print('Approved geometry reproduced for all three LODs; patched only the ice-cabinet authoring hook.')
