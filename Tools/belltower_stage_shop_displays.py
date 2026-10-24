"""Stage a small supplemental display mesh without rewriting the shared town models."""
import hashlib
import argparse
import json
from pathlib import Path
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_shop_displays as S

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/shop-displays/stage-v1'
RESOURCE = 'models/maps/belltower/shop-display-v1'
NAME = 'shop_displays'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def apertures(path):
    vertices, normals, faces = [None], [None], []
    material = None
    for line in path.open():
        if line.startswith('v '):
            x,y,z=map(float,line.split()[1:]); vertices.append(np.array((-x,z,y)))
        elif line.startswith('vn '):
            x,y,z=map(float,line.split()[1:]); normals.append(np.array((-x,z,y)))
        elif line.startswith('usemtl '):
            material=line.split()[1]
        elif line.startswith('f ') and material.startswith('shopfront_'):
            fields=[list(map(int,token.split('/'))) for token in line.split()[1:]]
            faces.append((material,fields))
    assert len(faces)==18
    records=[]
    for i in range(0,len(faces),2):
        a,b=faces[i:i+2]; assert a[0]==b[0]
        indices=sorted({f[0] for f in a[1]+b[1]}); assert len(indices)==4
        points=np.array([vertices[k] for k in indices]); n=normals[a[1][0][2]]
        assert abs(n[2])<1e-6 and np.isclose(np.linalg.norm(n),1)
        r=np.cross(n,(0,0,1));origin=points.mean(axis=0);origin[2]=points[:,2].min()
        width=float(np.ptp(points@r));height=float(np.ptp(points[:,2]))
        assert 50<width<=132.01 and height==104
        records.append(dict(origin=origin.tolist(),outward=n.tolist(),width=width,height=height,material=a[0]))
    return records


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args();OUT=args.out.resolve()
    assert OUT.is_relative_to(ROOT/'output/belltower/shop-displays')
    if (OUT/'manifest.json').exists():raise FileExistsError('Preserve the existing staged review.')
    records=apertures(ROOT/'Assets/models/maps/belltower/belltower_west.obj')
    model=K.Model();D.configure(model)
    for record in records:S.build(model,**{k:record[k] for k in ('origin','outward','width','height')})
    model.extend(model.mirrored())
    assert not model.boxes and not model.hulls and not model.props
    for paint,faces in model.polygons.items():
        for points,normal in faces:
            assert np.isfinite(points).all()
            assert np.dot(np.cross(points[1]-points[0],points[2]-points[0]),normal)>0
    folder=OUT/'Assets'/RESOURCE;folder.mkdir(parents=True,exist_ok=True)
    K.write_obj(folder/(NAME+'.obj'),model,NAME)
    K.write_vmdl(folder/(NAME+'.vmdl'),RESOURCE,NAME,model)
    for paint in S.COLOURS:
        p=OUT/'Assets'/S.RESOURCE/(paint.removeprefix('shop_')+'.vmat');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(S.material_text(paint),encoding='utf8',newline='\n')
    for key in 'abc':
        p=OUT/f'Assets/materials/belltower/shopfront_{key}.vmat';p.parent.mkdir(parents=True,exist_ok=True)
        text=S.glass_material_text();assert text
        p.write_text(text,encoding='utf8',newline='\n')
    files={}
    for p in (OUT/'Assets').rglob('*'):
        if p.is_file():
            rel=p.relative_to(OUT).as_posix();live=ROOT/rel
            files[rel]={'before':sha(live) if live.exists() else None,'after':sha(p)}
    scene=ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
    manifest={'revision':'shop-displays-v1','displays':18,'west_apertures':records,
        'triangles':model.triangle_count(),'new_colliders':0,'town_models_rebuilt':False,
        'model_path':RESOURCE+'/'+NAME+'.vmdl','files':files,
        'source_sha256':{p:sha(ROOT/p) for p in ['Tools/belltower_shop_displays.py','Tools/belltower_stage_shop_displays.py','Tools/belltower_furniture.py','Tools/map_kit.py']},
        'town_model_sha256':{f'Assets/models/maps/belltower/belltower_{side}.{ext}':sha(ROOT/f'Assets/models/maps/belltower/belltower_{side}.{ext}') for side in ('centre','west','east') for ext in ('obj','vmdl')},
        'staging_scene_sha256':sha(scene),'integration':'One visual-only ModelRenderer on the existing identity-transform Town object. Future complete map regeneration embeds the same builder in the town model and drops this supplemental renderer.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'displays':18,'triangles':manifest['triangles'],'files':len(files),'town_models_unchanged':True,'collision_unchanged':True,'apertures':records}))


if __name__=='__main__':main()
