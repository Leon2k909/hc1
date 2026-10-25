"""Replace only the already-installed shed append blocks, preserving their indices."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import belltower_stage_shed_corners as S

OUT=S.BASE/'r5/stage'
CACHE=S.BASE/'r2/stage'


def replace_block(source, old_piece, new_piece):
    old_lines=old_piece.read_bytes().splitlines(keepends=True)
    new_lines=new_piece.read_bytes().splitlines(keepends=True)
    kinds=(b'v ',b'vt ',b'vn ')
    assert all(sum(l.startswith(k) for l in old_lines)==sum(l.startswith(k) for l in new_lines) for k in kinds)
    assert [l for l in old_lines if l.startswith((b'f ',b'usemtl '))]==[l for l in new_lines if l.startswith((b'f ',b'usemtl '))]
    table_block=b''.join(l for l in old_lines if l.startswith(kinds))
    before=S.sha(source); data=source.read_bytes()
    assert data.count(table_block)==1,('The selected shed tables changed',source)
    start=data.index(table_block)
    following=data[start+len(table_block):].split(b'\n',3)
    installed_face=next(l for l in following if l.startswith(b'f '))
    cached_face=next(l for l in old_lines if l.startswith(b'f '))
    a=tuple(map(int,installed_face.split()[1].split(b'/')))
    b=tuple(map(int,cached_face.split()[1].split(b'/')))
    counts=dict(zip(('v','vt','vn'),(x-y for x,y in zip(a,b))))
    old_tail=S.append_bytes(old_piece,counts); new_tail=S.append_bytes(new_piece,counts)
    assert data[start:start+len(old_tail)]==old_tail
    assert [l for l in old_tail.splitlines() if l.startswith((b'f ',b'usemtl '))]==[l for l in new_tail.splitlines() if l.startswith((b'f ',b'usemtl '))]
    result=data[:start]+new_tail+data[start+len(old_tail):]
    relative=source.relative_to(S.ROOT); target=OUT/relative; backup=OUT/'before'/relative
    target.parent.mkdir(parents=True,exist_ok=True); backup.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(result); backup.write_bytes(data)
    assert S.sha(source)==before==S.sha(backup)
    return dict(before=before,after=S.sha(target),retained_prefix_sha256=hashlib.sha256(data[:start]).hexdigest(),
                retained_suffix_sha256=hashlib.sha256(data[start+len(old_tail):]).hexdigest(),all_existing_indices_preserved=True)


def main():
    assert not (OUT/'manifest.json').exists(); OUT.mkdir(parents=True,exist_ok=True)
    _,piece=S.difference()
    assert piece.triangle_count()==36960
    report=copy.deepcopy(json.loads((S.BASE/'r4/stage/manifest.json').read_text()))
    report['stage_revision']='r5'; report['files']={}; report['input_guards']={}
    report['source_sha256']={p:S.sha(S.ROOT/p) for p in report['source_sha256']}
    report['source_sha256']['Tools/belltower_refine_shed_corners.py']=S.sha(Path(__file__))
    report['scene_sha256']=S.sha(S.ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
    report['refinement']='Correct narrow-edge grain and soften the exposed trim arrises; topology unchanged.'
    for side in ('west','east'):
        model=piece if side=='west' else piece.mirrored(); name='belltower_'+side
        full=OUT/(name+'-timber.obj'); S.K.write_obj(full,model,name)
        source=S.ROOT/f'Assets/models/maps/belltower/{name}.obj'
        report['files'][source.relative_to(S.ROOT).as_posix()]=replace_block(source,CACHE/full.name,full)
        for item in report['models'][side]['imports']:
            if not item['receives_new_timber']:continue
            paint=next(p for p in sorted(S.PAINTS,key=len,reverse=True) if item['asset'].endswith('_'+p+'.obj'))
            part=S.K.Model(); part.polygons[paint]=model.polygons[paint]
            part.polygon_uvs={k:v for k,v in model.polygon_uvs.items() if k[0]==paint}
            part.polygon_normals={k:v for k,v in model.polygon_normals.items() if k[0]==paint}
            S.D.configure(part)
            temp=OUT/(name+'-'+paint+'.obj'); S.K.write_obj(temp,part,name)
            report['files'][item['asset']]=replace_block(S.ROOT/item['asset'],CACHE/temp.name,temp)
        for suffix in ('.vmdl','.mtl'):
            path=source.with_suffix(suffix); report['input_guards'][path.relative_to(S.ROOT).as_posix()]=S.sha(path)
        print(json.dumps(dict(side=side,triangles=piece.triangle_count(),existing_indices_preserved=True)),flush=True)
    assert len(report['files'])==6
    assert all(S.sha(S.ROOT/p)==row['before'] for p,row in report['files'].items())
    (OUT/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(stage=str(OUT),files=6)),flush=True)


if __name__=='__main__':main()
