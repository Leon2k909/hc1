"""Stage circular clock geometry by changing only the existing four clock patches.

The rest of the installed centre mesh, all collision and the original textures
stay intact. Publish the single OBJ through the native editor's guarded import.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path
import numpy as np
import map_kit as K
import belltower_detail as D
import belltower_clock as Clock
import belltower_map as B

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/clock-v1/stage'
RELATIVE='Assets/models/maps/belltower/belltower_centre.obj'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def old_clocks():
    model=K.Model()
    for centre,axis in Clock.POSES:
        out=np.array((axis[1],-axis[0],0.0))
        along=np.array((*axis,0.0))
        c=np.array((*centre,690.0))
        for half,depth,paint in ((52,1.0,'ashlar_grey'),(40,2.0,'clock')):
            points=[c+out*depth+along*sa*half+np.array((0,0,sz*half))
                    for sa,sz in ((-1,-1),(1,-1),(1,1),(-1,1))]
            B.facing(model,paint,points,out)
            if paint=='ashlar_grey':
                for k in range(4):
                    a,b=points[k],points[(k+1)%4]
                    B.facing(model,paint,[a,b,b-out*depth,a-out*depth],(a+b)/2-c)
    return model


def keys(model):
    result=Counter()
    for paint,faces in model.polygons.items():
        for points,_ in faces:
            p=[K.obj_vector(K.to_world(v)) for v in points]
            for k in range(1,len(p)-1):
                result[(paint,frozenset((p[0],p[k],p[k+1])))]+=1
    return result


def main():
    if (OUT/'manifest.json').exists():
        raise FileExistsError('Clock staging already exists; preserve the recorded stage.')
    OUT.mkdir(parents=True,exist_ok=True)
    model=K.Model();Clock.build(model);D.configure(model)
    assert not model.boxes and not model.hulls
    assert set(model.polygons)=={'clock','door_brass'}
    for paint,faces in model.polygons.items():
        for points,normal in faces:
            for k in range(1,len(points)-1):
                cross=np.cross(points[k]-points[0],points[k+1]-points[0])
                assert np.dot(cross,normal)>1e-8,(paint,'invalid triangle')
    wanted=keys(old_clocks());assert sum(wanted.values())==48
    source=ROOT/RELATIVE;raw=source.read_bytes();lines=raw.splitlines(keepends=True)
    vertices=[None];counts={'v':0,'vt':0,'vn':0};found=Counter();remove=[];paint=None
    for i,line in enumerate(lines):
        if line.startswith(b'v '):vertices.append(line[2:].strip().decode());counts['v']+=1
        elif line.startswith(b'vt '):counts['vt']+=1
        elif line.startswith(b'vn '):counts['vn']+=1
        elif line.startswith(b'usemtl '):paint=line[7:].strip().decode()
        elif line.startswith(b'f '):
            key=(paint,frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
            if key in wanted:found[key]+=1;remove.append(i)
    assert found==wanted and len(remove)==48,(found-wanted,wanted-found)
    piece=OUT/'round-clocks.obj';K.write_obj(piece,model,'belltower_centre')
    piece_lines=piece.read_bytes().splitlines(keepends=True)
    tables=[line for line in piece_lines if line.startswith((b'v ',b'vt ',b'vn '))]
    faces=[]
    for line in piece_lines:
        if line.startswith(b'usemtl '):faces.append(line)
        elif line.startswith(b'f '):
            tokens=[]
            for token in line.split()[1:]:
                a,b,c=map(int,token.split(b'/'))
                tokens.append(f'{a+counts["v"]}/{b+counts["vt"]}/{c+counts["vn"]}')
            faces.append(('f '+' '.join(tokens)+'\n').encode())
    cut=next(i for i,line in enumerate(lines) if line.startswith(b'usemtl '));drop=set(remove)
    result=b''.join(lines[:cut]+tables+[line for i,line in enumerate(lines[cut:],cut) if i not in drop]+faces)
    assert result.count(b'\nf ')==raw.count(b'\nf ')-48+model.triangle_count()
    target=OUT/RELATIVE;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
    # Original model remaps already contain both materials; no resource changes.
    mtl=source.with_suffix('.mtl').read_text();vmdl=source.with_suffix('.vmdl').read_text()
    assert all(f'newmtl {name}\n' in mtl for name in model.polygons)
    assert all(f'from = "{name}.vmat"' in vmdl for name in model.polygons)
    manifest={'revision':'round-clock-v1','path':RELATIVE,'before':sha(source),'after':sha(target),
              'removed_triangles':48,'added_triangles':model.triangle_count(),'removed_face_lines':remove,
              'vmdl_sha256':sha(source.with_suffix('.vmdl')),'mtl_sha256':sha(source.with_suffix('.mtl')),
              'scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
              'source_sha256':{p:sha(ROOT/p) for p in ('Tools/belltower_clock.py','Tools/belltower_stage_clock.py','Tools/map_kit.py','Tools/belltower_furniture.py')},
              'texture_sha256':{str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in
                              (ROOT/'Assets/materials/buildings').glob('clock_*.png')},
              'physics_unchanged':True,'other_mesh_lines_preserved':True}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({key:manifest[key] for key in ('revision','removed_triangles','added_triangles','physics_unchanged')}))


if __name__=='__main__':main()
