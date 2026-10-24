"""Replace only the two old gazebo roofs in the installed town."""
from array import array
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_gazebo as G

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/gazebo-v1/stage'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def key(points):
    return frozenset(tuple(round(float(x),3) for x in p) for p in points)


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args()
    OUT=args.out.resolve()
    assert OUT.is_relative_to(ROOT/'output/belltower')
    assert not (OUT/'manifest.json').exists(),'Preserve the first stage.'
    OUT.mkdir(parents=True,exist_ok=True)
    old=K.Model();B.cone(old,(-500,-1130),72,48,102,'copper',sides=6,turn=0.)
    new=K.Model();G.build(new);D.configure(new)
    for paint,faces in new.polygons.items():
        for points,normal in faces:
            assert np.isfinite(points).all()
            for i in range(1,len(points)-1):
                assert np.dot(np.cross(points[i]-points[0],points[i+1]-points[0]),normal)>1e-9,(paint,i)
    assert not new.boxes and not new.hulls and not new.props
    files={};models={}
    for side in ('west','east'):
        name='belltower_'+side
        before=old if side=='west' else old.mirrored()
        candidate=new if side=='west' else new.mirrored()
        wanted=Counter()
        for points,_ in before.polygons['copper']:
            xyz=[tuple(map(float,K.obj_vector(K.to_world(p)).split())) for p in points]
            for k in range(1,len(xyz)-1):wanted[key((xyz[0],xyz[k],xyz[k+1]))]+=1
        source=ROOT/f'Assets/models/maps/belltower/{name}.obj'
        # Keep only compact numeric vertex positions while scanning a large OBJ.
        vertices=array('d',(0.,0.,0.));offset={'v':0,'vt':0,'vn':0};paint=None;remove=[];found=Counter()
        with source.open('rb') as stream:
            for index,line in enumerate(stream):
                if line.startswith(b'v '):vertices.extend(map(float,line.split()[1:]));offset['v']+=1
                elif line.startswith(b'vt '):offset['vt']+=1
                elif line.startswith(b'vn '):offset['vn']+=1
                elif line.startswith(b'usemtl '):paint=line[7:].strip().decode()
                elif line.startswith(b'f ') and paint=='copper':
                    ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
                    points=[vertices[i*3:i*3+3] for i in ids]
                    k=key(points)
                    if k in wanted:remove.append(index);found[k]+=1
        assert found==wanted and len(remove)==10,(side,found,wanted)
        piece=OUT/(name+'-roof.obj');K.write_obj(piece,candidate,name)
        tables=[];faces=[]
        for line in piece.read_bytes().splitlines(keepends=True):
            if line.startswith((b'v ',b'vt ',b'vn ')):tables.append(line)
            elif line.startswith(b'usemtl '):faces.append(line)
            elif line.startswith(b'f '):
                indices=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'));indices.append(f'{a+offset["v"]}/{b+offset["vt"]}/{c+offset["vn"]}')
                faces.append(('f '+' '.join(indices)+'\n').encode())
        target=OUT/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True)
        drop=set(remove);inserted=False
        with source.open('rb') as src,target.open('wb') as dst:
            for index,line in enumerate(src):
                if not inserted and line.startswith(b'usemtl '):dst.writelines(tables);inserted=True
                if index not in drop:dst.write(line)
            dst.writelines(faces)
        assert inserted
        extra=tuple(p for p in candidate.polygons if p.startswith('gazebo_'))
        mtl=source.with_suffix('.mtl');mtl_after=mtl.read_bytes()
        for p in extra:
            assert f'newmtl {p}\n'.encode() not in mtl_after
            mtl_after+=f'newmtl {p}\nKd 1 1 1\nd 1\n'.encode()
        target.with_suffix('.mtl').write_bytes(mtl_after)
        vmdl=source.with_suffix('.vmdl');original=vmdl.read_bytes()
        anchor=next(line for line in original.splitlines(keepends=True) if b'from = "copper.vmat"' in line)
        indent=anchor[:len(anchor)-len(anchor.lstrip())]
        remaps=b''.join(indent+f'{{ from = "{p}.vmat" to = "{candidate.material_overrides[p]}" }},\n'.encode() for p in extra)
        assert original.count(anchor)==1
        target.with_suffix('.vmdl').write_bytes(original.replace(anchor,remaps+anchor))
        models[name]={'removed_faces':remove,'removed_triangles':10,'added_triangles':candidate.triangle_count(),
                      'old_vertex_counts':offset,'vmdl_inserted_remaps':remaps.decode(),'non_roof_bytes_preserved':True,'physics_byte_identical':True}
    for paint,text in G.materials().items():
        p=OUT/'Assets'/G.RESOURCE/(paint+'.vmat');p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf8')
    for p in sorted((OUT/'Assets').rglob('*')):
        if not p.is_file():continue
        rel=p.relative_to(OUT).as_posix();installed=ROOT/rel
        files[rel]={'before':sha(installed) if installed.exists() else None,'after':sha(p)}
        if installed.exists():
            backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(installed,backup)
    manifest={'revision':'gazebo-roof-v1','models':models,'files':files,
        'source_sha256':{p:sha(ROOT/p) for p in ['Tools/belltower_gazebo.py','Tools/belltower_stage_gazebo.py','Tools/map_kit.py','Tools/belltower_furniture.py']},
        'texture_sha256':{p:sha(ROOT/p) for p in ['Assets/materials/buildings/copper_color.png','Assets/materials/buildings/copper_brown_color.png','Assets/materials/buildings/copper_rough.png']},
        'scene_sha256_at_stage':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
        'scene_changed_by_this_task':False,'collision_changed':False,'texture_pixels_changed':False}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'staged_assets':len(files),'roofs':2,'triangles_per_roof':new.triangle_count(),'removed_triangles_per_roof':10,'scene_and_collision_unchanged':True}))


if __name__=='__main__':main()
