"""Stage only shipping-crate triangles, retaining every other installed town byte."""
import hashlib
import argparse
import importlib.util
import json
import shutil
from collections import Counter
from pathlib import Path
import numpy as np
import belltower_map as B
import belltower_detail as D
import belltower_furniture as F
import belltower_crates as C
import map_kit as K

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/crates-v2/stage'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def placements():
    """Consume the original layout RNG, omitting purely visual mesh work."""
    result=[]
    class NullModel(K.Model):
        def polygon(self,*args,**kwargs):pass
        def box(self,*args,**kwargs):pass
        def oriented_box(self,*args,**kwargs):pass
        def cylinder(self,*args,**kwargs):pass
        def beam(self,*args,**kwargs):pass
        def hull(self,*args,**kwargs):pass
        def collision_box(self,*args,**kwargs):pass
    def record(model,p,size):
        result.append({'origin':p.o.tolist(),'x':p.x.tolist(),'y':p.y.tolist(),'size':float(size)})
    saved=(B.Model,F.crate,F.bevel_box,F.turned,F.face)
    try:
        B.Model=NullModel;F.crate=record
        F.bevel_box=F.turned=F.face=lambda *args,**kwargs:None
        B.build_west([],np.random.default_rng(2024))
    finally:B.Model,F.crate,F.bevel_box,F.turned,F.face=saved
    assert result
    return result


def frame(row):
    p=B.Place(row['origin']);p.x=np.array(row['x']);p.y=np.array(row['y'])
    return p


def keys(model):
    result=Counter()
    for paint,faces in model.polygons.items():
        for points,_ in faces:
            p=[K.obj_vector(K.to_world(v)) for v in points]
            for i in range(1,len(p)-1):result[(paint,frozenset((p[0],p[i],p[i+1])))]+=1
    return result


def main():
    global OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=OUT)
    args=parser.parse_args();OUT=args.out.resolve()
    assert OUT.is_relative_to(ROOT/'output/belltower')
    assert not (OUT/'manifest.json').exists(),'Keep prior staging evidence'
    OUT.mkdir(parents=True,exist_ok=True)
    locations=placements()
    legacy_path=ROOT/'output/belltower/crates-v2/before/Tools/belltower_furniture.py'
    spec=importlib.util.spec_from_file_location('belltower_crate_legacy_v1',legacy_path)
    legacy=importlib.util.module_from_spec(spec);spec.loader.exec_module(legacy)
    previous=K.Model();candidate=K.Model()
    for row in locations:
        legacy.crate(previous,frame(row),row['size'])
        C.build(candidate,frame(row),row['size'])
    D.configure(candidate)
    assert not candidate.boxes and not candidate.hulls and not candidate.props
    for paint,faces in candidate.polygons.items():
        for p,n in faces:
            assert np.isfinite(p).all()
            for i in range(1,len(p)-1):
                cross=np.cross(p[i]-p[0],p[i+1]-p[0])
                assert np.linalg.norm(cross)>1e-9 and np.dot(cross,n)>0,(paint,'invalid triangle')
    manifest={'revision':'crate-joinery-v2','crates_per_half':len(locations),'placements':locations,
        'removed_triangles_per_half':previous.triangle_count(),'added_triangles_per_half':candidate.triangle_count(),
        'source_sha256':{f'Tools/{p}':sha(ROOT/'Tools'/p) for p in ('belltower_map.py','belltower_detail.py',
            'belltower_furniture.py','belltower_crates.py','belltower_stage_crates.py','map_kit.py')},
        'models':{},'files':{},'scene_edit_required':False,'collision_changes':0}
    for side in ('west','east'):
        name='belltower_'+side;rel=f'Assets/models/maps/belltower/{name}.obj';source=ROOT/rel
        old=previous if side=='west' else previous.mirrored()
        new=candidate if side=='west' else candidate.mirrored()
        wanted=keys(old);found=Counter();drop=set();vertices=[None];offset={'v':0,'vt':0,'vn':0};material=None
        before_hash=sha(source)
        with source.open('rb') as stream:
            for index,line in enumerate(stream):
                if line.startswith(b'v '):vertices.append(line[2:].strip().decode());offset['v']+=1
                elif line.startswith(b'vt '):offset['vt']+=1
                elif line.startswith(b'vn '):offset['vn']+=1
                elif line.startswith(b'usemtl '):material=line[7:].strip().decode()
                elif line.startswith(b'f ') and material in (F.WOOD,F.DARK,F.IRON):
                    key=(material,frozenset(vertices[int(t.split(b'/')[0])] for t in line.split()[1:]))
                    if key in wanted:found[key]+=1;drop.add(index)
        assert found==wanted and len(drop)==previous.triangle_count(),(side,sum(found.values()),sum(wanted.values()),len(wanted-found))
        del vertices
        piece=OUT/(name+'-crates.obj');K.write_obj(piece,new,name)
        raw=piece.read_bytes().splitlines(keepends=True)
        tables=[line for line in raw if line.startswith((b'v ',b'vt ',b'vn '))];tail=[]
        for line in raw:
            if line.startswith(b'usemtl '):tail.append(line)
            elif line.startswith(b'f '):
                tokens=[]
                for token in line.split()[1:]:
                    a,b,c=map(int,token.split(b'/'));tokens.append(f'{a+offset["v"]}/{b+offset["vt"]}/{c+offset["vn"]}')
                tail.append(('f '+' '.join(tokens)+'\n').encode())
        target=OUT/rel;target.parent.mkdir(parents=True,exist_ok=True)
        inserted=False
        with source.open('rb') as old_stream,target.open('wb') as updated:
            for index,line in enumerate(old_stream):
                if not inserted and line.startswith(b'usemtl '):
                    updated.writelines(tables);inserted=True
                if index not in drop:updated.write(line)
            assert inserted;updated.writelines(tail)
        assert sha(source)==before_hash,'Installed model changed during staging'
        # Reuse the already installed end-grain material with one extra mapping.
        mtl=source.with_suffix('.mtl');mtl_bytes=mtl.read_bytes();extra_mtl=b''
        if b'newmtl garden_endgrain\n' not in mtl_bytes:extra_mtl=b'newmtl garden_endgrain\nKd 1 1 1\nd 1\n'
        target.with_suffix('.mtl').write_bytes(mtl_bytes+extra_mtl)
        vmdl=source.with_suffix('.vmdl');vmdl_bytes=vmdl.read_bytes();extra_vmdl=b''
        if b'from = "garden_endgrain.vmat"' not in vmdl_bytes:
            anchor=next(line for line in vmdl_bytes.splitlines(keepends=True) if b'from = "furniture_wood.vmat"' in line)
            space=anchor[:len(anchor)-len(anchor.lstrip())]
            extra_vmdl=space+f'{{ from = "garden_endgrain.vmat" to = "{C.END_MATERIAL}" }},\n'.encode()
            vmdl_bytes=vmdl_bytes.replace(anchor,extra_vmdl+anchor)
        target.with_suffix('.vmdl').write_bytes(vmdl_bytes)
        manifest['models'][name]={'removed_face_lines':sorted(drop),'old_vertex_counts':offset,
            'mtl_suffix':extra_mtl.decode(),'vmdl_inserted_remap':extra_vmdl.decode(),
            'non_crate_obj_bytes_preserved':True,'physics_byte_identical':True}
        for installed in (source,mtl,vmdl):
            relative=installed.relative_to(ROOT);staged=OUT/relative;backup=OUT/'before'/relative
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(installed,backup)
            manifest['files'][relative.as_posix()]={'before':sha(installed),'after':sha(staged)}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('crates_per_half','removed_triangles_per_half','added_triangles_per_half','collision_changes')}))


if __name__=='__main__':main()
