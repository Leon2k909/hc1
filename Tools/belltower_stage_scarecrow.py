"""Replace only the original scarecrow faces in the installed town meshes.

Staging never writes Assets. Original vertex tables, all other faces, collision,
foliage and scene data are retained; the open editor publishes checked files.
"""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_detail as D
import belltower_scarecrow as S

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/scarecrow-v1/stage'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def keys(model):
    result=Counter()
    for paint,faces in model.polygons.items():
        for points,n in faces:
            p=[K.obj_vector(K.to_world(v)) for v in points]
            for i in range(1,len(p)-1):result[(paint,frozenset((p[0],p[i],p[i+1])))]+=1
    return result


def original():
    model=K.Model();p=B.Place((-1590,-1345,B.GARDEN_Z),0)
    p.beam(model,(0,0,0),(0,0,74),(3,3),'planks_dark')
    p.beam(model,(-24,0,56),(24,0,56),(3,3),'planks_dark')
    p.box(model,(-12,-6,30),(12,6,60),'canvas_green')
    B.blob(model,p.at((0,0,68)),7,'canvas_plain',squash=1.1,segments=6,rings=4,seed=4)
    B.cone(model,p.at((0,0,0))[:2],12,B.GARDEN_Z+73,B.GARDEN_Z+84,'canvas_plain',sides=8)
    assert not model.boxes and not model.hulls and not model.props
    return model


def main():
    assert not (OUT/'manifest.json').exists(),'Preserve the staged revision.'
    old=original();new=K.Model();S.build(new,B.Place((-1590,-1345,B.GARDEN_Z),0));D.configure(new)
    assert not new.boxes and not new.hulls and not new.props
    manifest={'revision':'scarecrow-v1','old_triangles_per_half':old.triangle_count(),
        'new_triangles_per_half':new.triangle_count(),'files':{},'models':{},
        'source_sha256':{p:sha(ROOT/p) for p in ['Tools/belltower_scarecrow.py','Tools/belltower_stage_scarecrow.py',
            'Tools/map_kit.py','Tools/belltower_furniture.py','Tools/belltower_map.py']},
        'scene_sha256_at_stage':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
        'scene_is_not_an_import_target':True,'collision_unchanged':True,'other_props_unchanged':True}
    for side in ('west','east'):
        name='belltower_'+side;relative=f'Assets/models/maps/belltower/{name}.obj';source=ROOT/relative
        wanted=keys(old if side=='west' else old.mirrored(B.EAST_PAINTS))
        wanted_positions={v for paint,points in wanted for v in points}
        sparse={};counts={'v':0,'vt':0,'vn':0};paint=None;found=Counter();drop=[]
        # Keep only the old prop's coordinates in memory, not the million-face town.
        with source.open('rb') as stream:
            for line_no,line in enumerate(stream):
                if line.startswith(b'v '):
                    counts['v']+=1;value=line[2:].strip().decode()
                    if value in wanted_positions:sparse[counts['v']]=value
                elif line.startswith(b'vt '):counts['vt']+=1
                elif line.startswith(b'vn '):counts['vn']+=1
                elif line.startswith(b'usemtl '):paint=line[7:].strip().decode()
                elif line.startswith(b'f '):
                    indices=[int(t.split(b'/')[0]) for t in line.split()[1:]]
                    if all(i in sparse for i in indices):
                        key=(paint,frozenset(sparse[i] for i in indices))
                        if key in wanted:found[key]+=1;drop.append(line_no)
        assert found==wanted and len(drop)==old.triangle_count(),(side,found-wanted,wanted-found)
        piece=new if side=='west' else new.mirrored(B.EAST_PAINTS)
        piece_path=OUT/(name+'-scarecrow.obj');K.write_obj(piece_path,piece,name)
        tables=[];faces=[]
        for line in piece_path.read_bytes().splitlines(keepends=True):
            if line.startswith((b'v ',b'vt ',b'vn ')):tables.append(line)
            elif line.startswith(b'usemtl '):faces.append(line)
            elif line.startswith(b'f '):
                shifted=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'))
                    shifted.append(f'{a+counts["v"]}/{b+counts["vt"]}/{c+counts["vn"]}')
                faces.append(('f '+' '.join(shifted)+'\n').encode())
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);remove=set(drop);inserted=False
        before_path=OUT/'before'/relative;before_path.parent.mkdir(parents=True,exist_ok=True)
        with source.open('rb') as incoming,target.open('wb') as updated,before_path.open('wb') as backup:
            for line_no,line in enumerate(incoming):
                backup.write(line)
                if not inserted and line.startswith(b'usemtl '):updated.writelines(tables);inserted=True
                if line_no not in remove:updated.write(line)
            updated.writelines(faces)
        assert inserted and sha(source)==sha(before_path)
        for ext in ('.mtl','.vmdl'):
            original_path=source.with_suffix(ext);dest=target.with_suffix(ext)
            raw=original_path.read_bytes();backup=before_path.with_suffix(ext);backup.write_bytes(raw)
            if ext=='.mtl':
                assert all(f'newmtl {paint}\n'.encode() not in raw for paint in S.MATERIALS)
                extra=b''.join(f'newmtl {paint}\nKd 1 1 1\nd 1\n'.encode() for paint in S.MATERIALS)
                dest.write_bytes(raw+extra)
            else:
                anchor=next(l for l in raw.splitlines(keepends=True) if b'from = "canvas_green.vmat"' in l)
                whitespace=anchor[:len(anchor)-len(anchor.lstrip())]
                extra=b''.join(whitespace+f'{{ from = "{paint}.vmat" to = "{path}" }},\n'.encode() for paint,path in S.MATERIALS.items())
                assert raw.count(anchor)==1;dest.write_bytes(raw.replace(anchor,extra+anchor))
                assert dest.read_bytes().replace(extra,b'',1)==raw
        manifest['models'][name]={'removed_face_lines':drop,'old_vertex_counts':counts,
            'inserted_table_lines':len(tables),'appended_face_lines':len(faces),
            'all_non_scarecrow_obj_bytes_preserved':True,'vmdl_added_remaps':extra.decode()}
    for p in (OUT/'Assets').rglob('*'):
        if not p.is_file():continue
        rel=p.relative_to(OUT).as_posix();installed=ROOT/rel
        manifest['files'][rel]={'before':sha(installed) if installed.exists() else None,'after':sha(p)}
    texture_paths=[]
    for name in ('sack','canvas','rope'):
        texture_paths += [f'Assets/materials/stillhouse/sh_{name}_color.png',
            f'Assets/materials/stillhouse/{name}_normal.png',f'Assets/materials/stillhouse/{name}_rough.png']
    manifest['texture_sha256']={p:sha(ROOT/p) for p in texture_paths}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'scarecrows':2,'replaced_triangles_per_half':old.triangle_count(),
        'new_triangles_per_half':new.triangle_count(),'collision_unchanged':True,'scene_untouched':True,
        'all_other_town_mesh_bytes_preserved':True,'files':len(manifest['files'])}))


if __name__=='__main__':main()
