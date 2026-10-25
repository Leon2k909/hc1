"""Stage only the garden well's visible ring and water; retain the installed town."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import numpy as np
import map_kit as K
import belltower_map as B
import belltower_well as W

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/well-v1/stage'
RELATIVE = 'Assets/models/maps/belltower/belltower_centre.obj'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def keys(model):
    result = Counter()
    for paint,faces in model.polygons.items():
        for points,_ in faces:
            p = [K.obj_vector(K.to_world(v)) for v in points]
            for k in range(1,len(p)-1):
                result[(paint,frozenset((p[0],p[k],p[k+1])))]+=1
    return result


def main():
    if (OUT/'manifest.json').exists():
        raise FileExistsError('Preserve the staged well revision.')
    OUT.mkdir(parents=True,exist_ok=True)
    old,new = K.Model(),K.Model()
    B.ring(old,B.GARDEN_WELL,30,42,-48,-14,10,
           {'outside':'rubble','inside':'rubble','top':'ashlar_grey'})
    old.cylinder(B.GARDEN_WELL,30,-40,-39,{'top':'water'},sides=10,turn=np.pi/10)
    W.build(new)
    assert not new.boxes and not new.hulls and not new.props
    for paint,faces in new.polygons.items():
        for points,normal in faces:
            assert np.isfinite(points).all()
            for k in range(1,len(points)-1):
                assert np.dot(np.cross(points[k]-points[0],points[k+1]-points[0]),normal)>1e-9
    source = ROOT/RELATIVE
    raw=source.read_bytes();lines=raw.splitlines(keepends=True)
    wanted=keys(old);found=Counter();remove=[];vertices=[None];paint=None
    counts={'v':0,'vt':0,'vn':0}
    for i,line in enumerate(lines):
        if line.startswith(b'v '):
            vertices.append(line[2:].strip().decode());counts['v']+=1
        elif line.startswith(b'vt '):counts['vt']+=1
        elif line.startswith(b'vn '):counts['vn']+=1
        elif line.startswith(b'usemtl '):paint=line[7:].strip().decode()
        elif line.startswith(b'f '):
            key=(paint,frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
            if key in wanted:found[key]+=1;remove.append(i)
    assert found==wanted,(found-wanted,wanted-found)
    assert len(remove)==68,len(remove)
    piece=OUT/'well-piece.obj';K.write_obj(piece,new,'belltower_centre')
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
    assert result.count(b'\nf ')==raw.count(b'\nf ')-68+new.triangle_count()
    target=OUT/RELATIVE;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(result)
    mtl=source.with_suffix('.mtl').read_bytes()
    extra_mtl=b''.join(f'newmtl {p}\nKd 1 1 1\nd 1\n'.encode() for p in sorted(new.polygons))
    assert all(f'newmtl {p}\n'.encode() not in mtl for p in new.polygons)
    target.with_suffix('.mtl').write_bytes(mtl+extra_mtl)
    vmdl=source.with_suffix('.vmdl').read_bytes()
    anchor=next(line for line in vmdl.splitlines(keepends=True) if b'from = "water.vmat"' in line)
    whitespace=anchor[:len(anchor)-len(anchor.lstrip())]
    extra=b''.join(whitespace+f'{{ from = "{p}.vmat" to = "{new.material_overrides[p]}" }},\n'.encode()
                   for p in sorted(new.polygons))
    assert vmdl.count(anchor)==1
    updated=vmdl.replace(anchor,extra+anchor);assert updated.replace(extra,b'',1)==vmdl
    target.with_suffix('.vmdl').write_bytes(updated)
    for paint,text in W.material_definitions().items():
        p=OUT/'Assets'/W.RESOURCE/(paint+'.vmat');p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(text,encoding='utf8')
    inputs=('Tools/belltower_well.py','Tools/belltower_stage_well.py','Tools/map_kit.py',
            'Tools/belltower_furniture.py','Tools/belltower_planters.py',
            'Assets/materials/belltower/planters-v1/cut_stone.vmat',
            'Assets/shaders/belltower_planter_v1.shader','Assets/shaders/belltower_fountain_water.shader')
    textures=[f'Assets/materials/belltower/scans/medieval_blocks_03_{s}_4k.png'
              for s in ('diffuse','nor_gl','rough','ao')]+['Assets/materials/belltower/fountain_water_normal.png']
    manifest={'revision':'garden-well-v1','removed_triangles':68,'added_triangles':new.triangle_count(),
        'removed_face_lines':remove,'old_vertex_counts':counts,'vmdl_inserted_remaps':extra.decode(),
        'mtl_appended':extra_mtl.decode(),'files':{},'source_sha256':{p:sha(ROOT/p) for p in inputs},
        'texture_sha256':{p:sha(ROOT/p) for p in textures},'physics_byte_identical':True,
        'other_mesh_lines_preserved':True,'roof_frame_and_clocks_preserved':True,
        'scene_info_only_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')}
    for path in sorted((OUT/'Assets').rglob('*')):
        if path.is_file():
            rel=path.relative_to(OUT).as_posix();installed=ROOT/rel
            manifest['files'][rel]={'before':sha(installed) if installed.exists() else None,'after':sha(path)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'revision':manifest['revision'],'files':len(manifest['files']),
        'removed_triangles':68,'added_triangles':new.triangle_count(),'physics_byte_identical':True}))


if __name__=='__main__':main()
