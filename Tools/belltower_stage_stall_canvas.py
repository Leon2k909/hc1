"""Replace only the installed market canopy faces; preserve the rest of both town meshes."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
import map_kit as K
import belltower_map as B
import belltower_stall_canvas as C

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/canopy-cloth-v1/stage'
STALLS = [(e, 1410, 180, paint) for e, paint in
          [(-1700,'canvas_red'),(-1540,'canvas_plain'),(-1180,'canvas_green'),
           (-1020,'canvas_red'),(-620,'canvas_plain'),(-460,'canvas_green')]]
STALLS += [(e, 1140, 0, paint) for e, paint in
           [(-1600,'canvas_green'),(-1180,'canvas_red'),(-560,'canvas_plain')]]


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def old_canvas(model, p, paint):
    roof = [p.at(q) for q in [(-68,-40,108),(68,-40,108),(68,46,90),(-68,46,90)]]
    front = [p.at(q) for q in [(-68,46,90),(68,46,90),(68,46,80),(-68,46,80)]]
    for points, normal in [(roof,(0,0,1)),(roof,(0,0,-1)),(front,p.y),(front,-p.y)]:
        B.facing(model, paint, points, normal)


def keys(model):
    result = Counter()
    for paint, faces in model.polygons.items():
        for points, _ in faces:
            ps = [K.obj_vector(K.to_world(p)) for p in points]
            for i in range(1, len(ps)-1):
                result[(paint,frozenset((ps[0],ps[i],ps[i+1])))] += 1
    return result


def main():
    assert not (OUT/'manifest.json').exists(), 'Preserve existing stage evidence'
    OUT.mkdir(parents=True, exist_ok=True)
    old, new = K.Model(), K.Model()
    for e,n,yaw,paint in STALLS:
        p = B.Place((e,n,0),yaw)
        old_canvas(old,p,paint)
        C.build(new,p,60,32,paint)
    assert not new.boxes and not new.hulls and not new.props
    assert set(new.polygons) == set(old.polygons)
    for paint, faces in new.polygons.items():
        for index, (points, normal) in enumerate(faces):
            assert np.isfinite(points).all() and np.isfinite(normal).all()
            assert (paint,index) in new.polygon_uvs and (paint,index) in new.polygon_normals
            assert min(p[2] for p in points)>72 and max(p[2] for p in points)<111
            for i in range(1,len(points)-1):
                assert np.dot(np.cross(points[i]-points[0],points[i+1]-points[0]),normal)>1e-7
    manifest={'revision':'stall-canvas-v1','stalls_per_half':9,'models':{},'files':{},
              'removed_triangles_per_half':old.triangle_count(),'added_triangles_per_half':new.triangle_count(),
              'new_materials':0,'new_colliders':0,'guards':{},'source_sha256':{}}
    for f in ['Tools/belltower_stall_canvas.py','Tools/belltower_stage_stall_canvas.py','Tools/map_kit.py']:
        manifest['source_sha256'][f]=sha(ROOT/f)
    for side in ('west','east'):
        name='belltower_'+side
        before = old if side=='west' else old.mirrored(B.EAST_PAINTS)
        candidate = new if side=='west' else new.mirrored(B.EAST_PAINTS)
        wanted=keys(before);assert sum(wanted.values())==72
        positions=set().union(*(key[1] for key in wanted))
        relative=f'Assets/models/maps/belltower/{name}.obj'
        source=ROOT/relative;vertices={};offset={'v':0,'vt':0,'vn':0};found=Counter();remove=[];paint=None;cut=None
        with source.open('rb') as stream:
            for line_no,line in enumerate(stream):
                if line.startswith(b'v '):
                    offset['v']+=1;pos=line[2:].strip().decode()
                    if pos in positions:vertices[offset['v']]=pos
                elif line.startswith(b'vt '):offset['vt']+=1
                elif line.startswith(b'vn '):offset['vn']+=1
                elif line.startswith(b'usemtl '):
                    paint=line[7:].strip().decode()
                    if cut is None:cut=line_no
                elif line.startswith(b'f '):
                    ids=[int(t.split(b'/')[0]) for t in line.split()[1:]]
                    if all(i in vertices for i in ids):
                        key=(paint,frozenset(vertices[i] for i in ids))
                        if key in wanted:found[key]+=1;remove.append(line_no)
        assert found==wanted and len(remove)==72,(side,found-wanted,wanted-found)
        piece=OUT/(name+'-canvas.obj');K.write_obj(piece,candidate,name)
        lines=piece.read_bytes().splitlines(keepends=True)
        tables=[line for line in lines if line.startswith((b'v ',b'vt ',b'vn '))]
        faces=[]
        for line in lines:
            if line.startswith(b'usemtl '):faces.append(line)
            elif line.startswith(b'f '):
                tokens=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'))
                    tokens.append(f'{a+offset["v"]}/{b+offset["vt"]}/{c+offset["vn"]}')
                faces.append(('f '+' '.join(tokens)+'\n').encode())
        target=OUT/relative;target.parent.mkdir(parents=True,exist_ok=True);drop=set(remove)
        with source.open('rb') as original,target.open('wb') as staged:
            for index,line in enumerate(original):
                if index==cut:staged.writelines(tables)
                if index not in drop:staged.write(line)
            staged.writelines(faces)
        manifest['files'][relative]={'before':sha(source),'after':sha(target)}
        manifest['models'][name]={'removed_face_lines':remove,'original_counts':offset,
                                'all_other_lines_preserved':True,'source_table_end_line':cut}
        for extension in ('.vmdl','.mtl'):
            f=source.with_suffix(extension);manifest['guards'][f.relative_to(ROOT).as_posix()]=sha(f)
    # Scene placement may legitimately change in another chat; it is never an input
    # or output of this surgical model patch. The native publisher checks its own
    # before/after scene hash and state during the actual import.
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(json.dumps({k:manifest[k] for k in ('stalls_per_half','removed_triangles_per_half',
          'added_triangles_per_half','new_materials','new_colliders')}))


if __name__=='__main__':main()
