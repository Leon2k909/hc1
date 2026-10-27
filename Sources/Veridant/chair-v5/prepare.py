"""Convert/export and stage this chair only; installed game assets stay untouched."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import sys

import numpy as np

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
from belltower_safe_imports import span
from veridant_stage_chairs import placements
import veridant_chair_authored as C

SOURCE=Path(__file__).resolve().parent
OUT=ROOT/'output/veridant/chair-v5'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def pack():
    row=json.loads((OUT/'mesh.json').read_text(encoding='utf-8'))[0]
    positions=np.array(row['positions'],dtype=np.float32)
    normals=np.array(row['normals'],dtype=np.float32)
    uv=np.array(row['uv'],dtype=np.float32)
    combined=np.concatenate((positions,normals,uv),axis=1)
    unique,indices=np.unique(combined,axis=0,return_inverse=True)
    faces=indices.reshape(-1,3).astype(np.uint32)
    triangles=positions.reshape(-1,3,3)
    centres=triangles.mean(1)
    cross=np.cross(triangles[:,1]-triangles[:,0],triangles[:,2]-triangles[:,0])
    mask=(centres[:,2]>.40)&(centres[:,2]<.54)&(cross[:,2]>.00001)
    anchor=np.average(centres[mask],axis=0,weights=np.linalg.norm(cross[mask],axis=1))
    anchor[2]=float(positions[:,2].min())
    assert np.isfinite(unique).all() and len(faces)==22013
    assert np.allclose(np.linalg.norm(unique[:,3:6],axis=1),1.,atol=1e-5)
    np.savez_compressed(SOURCE/'mesh.npz',positions=unique[:,:3],normals=unique[:,3:6],
                        uv=unique[:,6:],faces=faces,anchor=anchor)


def write_obj(path,rows):
    path.parent.mkdir(parents=True,exist_ok=True)
    output=[f'mtllib {path.stem}.mtl\no {path.stem}\n']
    mesh=C.mesh();count=len(mesh['positions'])
    ps=[];ns=[];uvs=[];fs=[]
    for index,(at,facing,z0) in enumerate(rows):
        p,n,uv,faces=C.transform(at,facing,z0)
        # map_kit world: (N,-E,Z); OBJ axes: (world Y,world Z,world X).
        p=np.column_stack((-p[:,0],p[:,2],p[:,1]))
        n=np.column_stack((-n[:,0],n[:,2],n[:,1]))
        ps.extend('v '+' '.join(f'{v:.6f}' for v in point)+'\n' for point in p)
        ns.extend('vn '+' '.join(f'{v:.7f}' for v in normal)+'\n' for normal in n)
        uvs.extend('vt '+' '.join(f'{v:.7f}' for v in point)+'\n' for point in uv)
        fs.extend('f '+' '.join(f'{i}/{i}/{i}' for i in face+1+count*index)+'\n' for face in faces)
    assert count*len(rows)<65536
    output.extend(ps);output.extend(uvs);output.extend(ns);output.append('usemtl '+C.PAINT+'\n');output.extend(fs)
    path.write_bytes(''.join(output).encode('ascii'))
    path.with_suffix('.mtl').write_bytes(f'newmtl {C.PAINT}\nKd 1 1 1\nd 1\n'.encode('ascii'))
    return {'triangles':len(fs),'vertices':count*len(rows)}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='stage-v1')
    parser.add_argument('--refresh-source',action='store_true')
    args=parser.parse_args();assert re.fullmatch(r'stage-v\d+',args.stage)
    if args.refresh_source or not (SOURCE/'mesh.npz').exists():pack()
    stage=OUT/args.stage;assert not stage.exists(),'Preserve each stage'
    stage.mkdir(parents=True)
    rows=placements();paths=[];chunks=[]
    for start in range(0,len(rows),3):
        relative=Path(f'Assets/models/maps/veridant/chair-v5/chairs-{start//3}.obj')
        chunks.append(write_obj(stage/relative,rows[start:start+3]))
        paths.extend((relative,relative.with_suffix('.mtl')))
    material=Path('Assets/materials/veridant/chair-v5')
    (stage/material).mkdir(parents=True)
    maps={}
    for channel,suffix in (('TextureColor','diff'),('TextureNormal','nor_gl'),
                           ('TextureRoughness','rough'),('TextureAmbientOcclusion','ao')):
        filename=f'dining_chair_02_{suffix}_2k.png'
        relative=material/filename;shutil.copyfile(SOURCE/'textures'/filename,stage/relative)
        paths.append(relative);maps[channel]=relative.relative_to('Assets').as_posix()
    text='// CC0 Dining Chair 02, James Ray Cock / Poly Haven\n"Layer0"\n{\n'
    text+='    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n    g_flMetalness "0"\n'
    text+='    g_flRoughnessScaleFactor "1"\n    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n'
    text+=''.join(f'    {name} "{path}"\n' for name,path in maps.items())+'}\n'
    (stage/material/'leather.vmat').write_bytes(text.encode('utf-8'));paths.append(material/'leather.vmat')
    vmdl=Path('Assets/models/maps/veridant/veridant_dress.vmdl')
    before=(ROOT/vmdl).read_bytes().decode('utf-8');document=before
    if 'models/maps/veridant/chair-v4/chairs-0.obj' in document:
        markers=[f'filename = "models/maps/veridant/chair-v4/chairs-{i}.obj"' for i in (0,1)]
        a,b=span(document,markers[0]);template=document[a:b]
        replacements=[];nodes=[]
        for i in range(4):
            node=re.sub(r'name = "[^"]+"',f'name = "veridant_authored_chairs_{i}"',template,count=1)
            node=node.replace('models/maps/veridant/chair-v4/chairs-0.obj',f'models/maps/veridant/chair-v5/chairs-{i}.obj')
            nodes.append(node)
        replacements.append((a,b,',\r\n'.join(nodes)))
        a,b=span(document,markers[1]);end=b
        while end<len(document) and document[end].isspace():end+=1
        if document[end:end+1]==',':end+=1
        replacements.append((a,end,''))
        for a,b,value in sorted(replacements,reverse=True):document=document[:a]+value+document[b:]
        a,b=span(document,'_class = "DefaultMaterialGroup"');bracket=document.index('[',document.index('remaps =',a,b),b)+1
        assert f'from = "{C.PAINT}.vmat"' not in document
        document=document[:bracket]+f'\r\n{{ from = "{C.PAINT}.vmat" to = "{C.MATERIAL}" }},'+document[bracket:]
    else:
        assert all(document.count(f'models/maps/veridant/chair-v5/chairs-{i}.obj')==1 for i in range(4))
        assert document.count(f'from = "{C.PAINT}.vmat"')==1
    a,b=span(before,'_class = "PhysicsShapeList"');c,d=span(document,'_class = "PhysicsShapeList"')
    assert before[a:]==document[c:]
    (stage/vmdl).parent.mkdir(parents=True,exist_ok=True);(stage/vmdl).write_bytes(document.encode('utf-8'))
    if document!=before:paths.append(vmdl)
    entry=Path('Tools/veridant_chair.py');old=(ROOT/entry).read_bytes()
    new=old.replace(b'from veridant_chair_soft import build_into as build_soft',
                    b'from veridant_chair_authored import build_into as build_soft')
    assert b'from veridant_chair_authored import build_into as build_soft' in new
    (stage/entry).parent.mkdir(parents=True);(stage/entry).write_bytes(new)
    if new!=old:paths.append(entry)
    files={}
    for relative in paths:
        target=ROOT/relative;previous=sha(target) if target.exists() else None
        if previous==sha(stage/relative):continue
        if previous:
            backup=stage/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,backup)
        files[relative.as_posix()]={'before':previous,'after':sha(stage/relative),'source':(stage/relative).relative_to(ROOT).as_posix()}
    report={'revision':'veridant-authored-chair-v5','instances':len(rows),'triangles_per_chair':22013,
            'total_triangles':len(rows)*22013,'files':files,'chunks':chunks,'physics_suffix_exact':True,
            'source':'https://polyhaven.com/a/dining_chair_02','license':'CC0 1.0',
            'physical_scale_inches_per_metre':C.INCHES,
            'placements':[{'at':at.tolist(),'facing':f.tolist(),'z0':z} for at,f,z in rows]}
    (stage/'manifest.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:report[k] for k in ('instances','triangles_per_chair','total_triangles','chunks','physics_suffix_exact')},indent=2))


if __name__=='__main__':main()
