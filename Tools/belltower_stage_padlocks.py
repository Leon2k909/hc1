"""Stage six shed lock replacements without regenerating the town or its collision."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_gardens as G
import belltower_padlock as P

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/shed-padlock-v1/stage'
SHEDS=((-1840,-1720,-1440,-1340,'+n'),(-420,-300,-1440,-1360,'+n'),(-1440,-1380,-1090,-1030,'+e'))


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def models():
    old,new=K.Model(),K.Model()
    for e0,e1,n0,n1,door in SHEDS:
        origin=((e0+e1)/2+14,n1,-10) if door=='+n' else (e1,(n0+n1)/2+14,-10)
        axes=np.array(((1,0,0),(0,1,0),(0,0,1))) if door=='+n' else np.array(((0,1,0),(1,0,0),(0,0,1)))
        seed=G._seed(e0,n0,-48)+206
        P.old_handle(old,origin,axes,seed)
        P.build(new,origin,axes,seed)
    D.configure(new)
    assert old.triangle_count()==264 and not new.props and not new.boxes and not new.hulls
    return old,new


def keys(model):
    result=Counter()
    for paint,faces in model.polygons.items():
        for points,normal in faces:
            p=[K.obj_vector(K.to_world(v)) for v in points]
            for i in range(1,len(p)-1):result[paint,frozenset((p[0],p[i],p[i+1]))]+=1
    return result


def steel_material():
    return '''// Shed padlock shackle and hinge; existing normal/roughness pixels.
"Layer0"
{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    TextureColor "materials/default/default_color.tga"
    TextureNormal "materials/buildings/iron_normal.png"
    TextureRoughness "materials/buildings/iron_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[.48 .51 .54 1]"
    g_flMetalness ".95"
    g_flRoughnessScaleFactor ".48"
    g_flModelTintAmount "1"
}
'''


def main():
    assert not (OUT/'manifest.json').exists(),'Retain the recorded stage.'
    OUT.mkdir(parents=True,exist_ok=True)
    old,new=models()
    manifest={'revision':'shed-padlock-v1','locks':6,'removed_triangles_per_half':264,
              'added_triangles_per_half':new.triangle_count(),'files':{},'models':{},
              'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
              'source_sha256':{p:sha(ROOT/p) for p in ('Tools/belltower_padlock.py','Tools/belltower_stage_padlocks.py',
                    'Tools/belltower_gardens.py','Tools/belltower_furniture.py','Tools/map_kit.py','Tools/belltower_detail.py')},
              'collision_unchanged':True,'all_other_mesh_bytes_preserved':True}
    mat=OUT/'Assets'/P.STEEL_MATERIAL;mat.parent.mkdir(parents=True,exist_ok=True);mat.write_text(steel_material())
    for side in ('west','east'):
        name='belltower_'+side;rel=f'Assets/models/maps/belltower/{name}.obj';source=ROOT/rel
        before=old if side=='west' else old.mirrored();piece=new if side=='west' else new.mirrored()
        wanted=keys(before);vertex_set=set().union(*(key[1] for key in wanted));found=Counter();positions={};drop=[]
        count={'v':0,'vt':0,'vn':0};paint=None
        source_hash=sha(source)
        with source.open('rb') as f:
            for line_number,line in enumerate(f):
                if line.startswith(b'v '):
                    count['v']+=1;p=line[2:].strip().decode()
                    if p in vertex_set:positions[count['v']]=p
                elif line.startswith(b'vt '):count['vt']+=1
                elif line.startswith(b'vn '):count['vn']+=1
                elif line.startswith(b'usemtl '):paint=line[7:].strip().decode()
                elif paint=='iron_black' and line.startswith(b'f '):
                    coords=[positions.get(int(t.split(b'/')[0])) for t in line.split()[1:]]
                    if None in coords:continue
                    key=paint,frozenset(coords)
                    if key in wanted:found[key]+=1;drop.append(line_number)
        assert found==wanted and len(drop)==264,(side,len(drop),sum((wanted-found).values()))
        temp=OUT/(name+'-locks.obj');K.write_obj(temp,piece,name)
        lines=temp.read_bytes().splitlines(keepends=True)
        tables=[l for l in lines if l.startswith((b'v ',b'vt ',b'vn '))];tail=[]
        for line in lines:
            if line.startswith(b'usemtl '):tail.append(line)
            elif line.startswith(b'f '):
                indices=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'));indices.append(f'{a+count["v"]}/{b+count["vt"]}/{c+count["vn"]}')
                tail.append(('f '+' '.join(indices)+'\n').encode())
        target=OUT/rel;backup=OUT/'before'/rel
        target.parent.mkdir(parents=True,exist_ok=True);backup.parent.mkdir(parents=True,exist_ok=True)
        inserted=False;drop_set=set(drop)
        with source.open('rb') as src,target.open('wb') as dest,backup.open('wb') as saved:
            for i,line in enumerate(src):
                saved.write(line)
                if not inserted and line.startswith(b'usemtl '):dest.writelines(tables);inserted=True
                if i not in drop_set:dest.write(line)
            dest.writelines(tail)
        assert sha(backup)==source_hash==sha(source),'Town changed while staging'
        for suffix in ('.mtl','.vmdl'):
            p=source.with_suffix(suffix);saved=backup.with_suffix(suffix);shutil.copyfile(p,saved)
            content=p.read_bytes()
            if suffix=='.mtl':
                assert f'newmtl {P.STEEL}\n'.encode() not in content
                result=content+f'newmtl {P.STEEL}\nKd 1 1 1\nd 1\n'.encode()
            else:
                assert b'from = "door_brass.vmat"' in content
                anchor=next(l for l in content.splitlines(keepends=True) if b'from = "iron_black.vmat"' in l)
                indent=anchor[:len(anchor)-len(anchor.lstrip())]
                remap=indent+f'{{ from = "{P.STEEL}.vmat" to = "{P.STEEL_MATERIAL}" }},\n'.encode()
                assert content.count(anchor)==1;result=content.replace(anchor,remap+anchor)
                assert result.replace(remap,b'',1)==content
            target.with_suffix(suffix).write_bytes(result)
        manifest['models'][name]={'removed_face_lines':drop,'old_vertex_counts':count,
                                 'inserted_remap':remap.decode(),'non_hardware_bytes_preserved':True}
        print(json.dumps({'side':side,'removed':len(drop),'added':piece.triangle_count()}),flush=True)
    for p in sorted((OUT/'Assets').rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(OUT).as_posix();current=ROOT/rel
        manifest['files'][rel]={'before':sha(current) if current.exists() else None,'after':sha(p)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'staged':len(manifest['files']),'locks':6,'added_triangles_per_half':new.triangle_count()}))


if __name__=='__main__':main()
