from pathlib import Path
import sys,json,importlib.util,numpy as np
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/shelving-v1'
body=(HERE/'geometry.py').read_text(encoding='utf-8')
suffix='''
def append_to(target,position):
    import riverside_parts as P
    offset=np.asarray(position,float);m=P.place(model(0),offset,90)
    for paint,faces in m.polygons.items():
        alias="shv1_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))
    target.oriented_box(offset+np.array((0.,0.,28.)),(X,np.array((0.,1.,0.)),Z),(36,70,56),{"default":None},"wood")
'''
(ROOT/'Tools/riverside_shelving.py').write_text('"""Approved non-emissive grocery shelving; retain original shelf collisions."""\n'+body+suffix,encoding='utf-8')
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import riverside_shelving as S
for lod in range(3):
    path=OUT/f'generator-proof-{lod}.obj';K.write_obj(path,S.model(lod),f'gondola_lod{lod}')
    assert path.read_text().splitlines()[3:]==(REVIEW/f'Assets/models/maps/riverside/shelving-v1/gondola_lod{lod}.obj').read_text().splitlines()[3:]
test=K.Model();S.append_to(test,(140,765,20));assert len(test.boxes)==1 and np.allclose(test.boxes[0][0],(140,765,48)) and np.allclose(test.boxes[0][2],(36,70,56))
generator=ROOT/'Tools/riverside_map.py';text=generator.read_text(encoding='utf-8')
old='''            box( m, row_e - 18, row_e + 18, sn, sn + 70, F, F + 56, { "default": "rs_wood" }, "wood" )
            for zz in ( F + 18, F + 38, F + 56 ):
                P.lit( m, "window", v( row_e - 18.3, sn + 35, zz - 7 ), P.right_for( ( -1, 0 ) ), 12, off=0.0, w=68 )
                P.lit( m, "window", v( row_e + 18.3, sn + 35, zz - 7 ), P.right_for( ( 1, 0 ) ), 12, off=0.0, w=68 )'''
assert text.count(old)==1,'Shelving authoring changed; inspect before patching'
(OUT/'install-before/riverside_map.py').write_bytes(generator.read_bytes())
generator.write_text(text.replace(old,'''            from riverside_shelving import append_to as append_approved_shelving
            append_approved_shelving( m, v( row_e, sn + 35, F ) )'''),encoding='utf-8')
(OUT/'generator-verified.json').write_text(json.dumps(dict(all_lods_match_approved=True,old_shelf_authoring_removed=True,collision_unchanged=True,full_map_regenerated=False),indent=2),encoding='utf-8')
print('Approved shelf meshes reproduced; replaced only four old shelf authoring calls and retained their collisions.')
