from pathlib import Path
import sys,json,numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/counter-v1'
s=(HERE/'build.py').read_text(encoding='utf-8');body=s[s.index('X=np.array'):s.index('\ncounts=[]')]
head='''"""Approved Lucky Stop checkout counter, retaining the original wood box collision."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as G
MAT="materials/riverside/counter-v1"
'''
suffix='''
def append_to(target,position):
    m=model(0);offset=np.asarray(position,float)
    for paint,faces in m.polygons.items():
        alias="ctrv1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,[p+offset for p in points],normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    target.oriented_box(offset+np.array((0.,0.,20.)),(X,np.array((0.,1.,0.)),Z),(110,30,40),{"default":None},"wood")
'''
(ROOT/'Tools/riverside_counter.py').write_text(head+body+suffix,encoding='utf-8')
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import riverside_counter as C
for lod in range(3):
    proof=OUT/f'generator-proof-{lod}.obj';K.write_obj(proof,C.model(lod),f'counter_lod{lod}')
    assert proof.read_text().splitlines()[3:]==(REVIEW/f'Assets/models/maps/riverside/counter-v1/counter_lod{lod}.obj').read_text().splitlines()[3:]
target=K.Model();C.append_to(target,(135,935,20));assert len(target.boxes)==1 and np.allclose(target.boxes[0][0],(135,935,40)) and np.allclose(target.boxes[0][2],(110,30,40))
generator=ROOT/'Tools/riverside_map.py';text=generator.read_text(encoding='utf-8');old='    box( m, e0 + 10, e0 + 120, n1 - 80, n1 - 50, F, F + 40, { "default": "rs_wood", "+z": "rs_concrete" }, "wood" )';assert text.count(old)==1
(OUT/'install-before/riverside_map.py').write_bytes(generator.read_bytes())
generator.write_text(text.replace(old,'''    from riverside_counter import append_to as append_approved_counter
    append_approved_counter( m, v( e0 + 65, n1 - 65, F ) )'''),encoding='utf-8')
(OUT/'generator-verified.json').write_text(json.dumps(dict(all_lods_match_approved=True,old_counter_authoring_removed=True,collision_unchanged=True,full_map_regenerated=False),indent=2),encoding='utf-8')
print('Counter authoring replaced; all three approved meshes and the original collision verified.')
