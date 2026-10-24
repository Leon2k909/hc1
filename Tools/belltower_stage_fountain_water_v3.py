"""Stage only fountain water; keep the current lion, bell and town imports intact."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import belltower_fountain_water as W
import belltower_compact_obj as C
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/belltower/fountain-water-v3'


def sha(p):
    with p.open('rb') as stream: return hashlib.file_digest(stream,'sha256').hexdigest()


def replace_water(path,piece,target,paints):
    counts={k:0 for k in C.KINDS}
    for line in path.open('rb'):
        for kind in C.KINDS:
            if line.startswith(kind+b' '): counts[kind]+=1; break
    additions=[]; faces=[]; paint=None
    for line in piece.open('rb'):
        if line.startswith((b'v ',b'vt ',b'vn ')): additions.append(line)
        elif line.startswith(b'usemtl '):
            paint=line.split()[1]
            if paint in paints: faces.append(line)
        elif line.startswith(b'f ') and paint in paints:
            tokens=[b'/'.join(str(int(index)+counts[kind]).encode() for kind,index in zip(C.KINDS,token.split(b'/')))
                    for token in line.split()[1:]]
            faces.append(b'f '+b' '.join(tokens)+b'\n')
    kept=[]; removed=Counter(); paint=None
    for line in path.open('rb'):
        if line.startswith(b'usemtl '): paint=line.split()[1]
        if line.startswith(b'f ') and paint in paints: removed[paint.decode()]+=1
        else: kept.append(line)
    expected=b''.join(kept); at=expected.index(b'usemtl ')
    result=expected[:at]+b''.join(additions)+expected[at:]+b''.join(faces)
    target.parent.mkdir(parents=True,exist_ok=True); target.write_bytes(result)
    assert target.read_bytes().replace(b''.join(additions),b'',1)[:-len(b''.join(faces))]==expected
    return {'removed_triangles':dict(removed),'added_triangles':sum(x.startswith(b'f ') for x in faces),
            'retained_original_bytes_sha256':hashlib.sha256(expected).hexdigest(),'all_non_water_bytes_exact':True}


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--revision',default='revision1')
    parser.add_argument('--shader-only',action='store_true'); args=parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+',args.revision)
    stage=OUT/args.revision/'stage'; assert not (stage/'manifest.json').exists()
    stage.mkdir(parents=True,exist_ok=True)
    if args.shader_only:
        manifest={'revision':'fountain-water-v3','stage_revision':args.revision,'files':{},'geometry':{},
                  'source_sha256':{},'protected_sha256':{},'shader_only':True,
                  'scene_changed':False,'physics_changed':False,'lion_lily_bell_changed':False}
        for name in ('surface','stream'):
            filename=f'belltower_fountain_{name}_v3.shader'
            source=ROOT/'Sources/Belltower/shaders'/filename; path=ROOT/'Assets/shaders'/filename
            target=stage/path.relative_to(ROOT); target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(source,target)
            backup=stage/'before'/path.relative_to(ROOT); backup.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,backup)
            manifest['files'][path.relative_to(ROOT).as_posix()]={'source':target.relative_to(ROOT).as_posix(),
                'before':sha(path),'after':sha(target),'backup':backup.relative_to(ROOT).as_posix()}
            manifest['source_sha256'][source.relative_to(ROOT).as_posix()]=sha(source)
        vmdl=ROOT/'Assets/models/maps/belltower/belltower_centre.vmdl'; text=vmdl.read_text()
        a,b=span(text,'_class = "RenderMeshList"')
        refs=[ROOT/'Assets'/r for r in re.findall('filename = "([^"]+)"',text[a:b])]
        for p in [vmdl,vmdl.with_suffix('.obj'),vmdl.with_suffix('.mtl'),*refs,
                  ROOT/'Assets/scenes/maps/Belltower/belltower.scene',
                  ROOT/'Assets/materials/belltower/fountain_water.vmat',ROOT/'Assets/materials/belltower/fountain_jet.vmat']:
            manifest['protected_sha256'][p.relative_to(ROOT).as_posix()]=sha(p)
        (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
        print(json.dumps({'stage':str(stage),'files':2,'geometry_changed':False})); return
    model=K.Model(); W.build(model)
    assert not model.boxes and not model.hulls and not model.props
    for paint,polygons in model.polygons.items():
        for i,(points,normal) in enumerate(polygons):
            uv=model.polygon_uvs.get((paint,i))
            assert all(np.isfinite(p).all() for p in points)
            for j in range(1,len(points)-1):
                rounded=np.asarray([list(map(float,K.obj_vector(K.to_world(points[q])).split())) for q in (0,j,j+1)])
                assert np.linalg.norm(np.cross(rounded[1]-rounded[0],rounded[2]-rounded[0]))>1e-7
                if uv:
                    a,b,c=[np.asarray(uv[q]) for q in (0,j,j+1)]
                    assert abs(np.linalg.det(np.array((b-a,c-a))))>1e-9
    piece=stage/'water-only.obj'; K.write_obj(piece,model,'belltower_centre')
    vmdl=ROOT/'Assets/models/maps/belltower/belltower_centre.vmdl'
    text=vmdl.read_text(); a,b=span(text,'_class = "RenderMeshList"')
    refs=[ROOT/'Assets'/r for r in re.findall('filename = "([^"]+)"',text[a:b])]
    targets={ROOT/'Assets/models/maps/belltower/belltower_centre.obj':{b'fountain_water',b'fountain_jet'}}
    for paint in ('fountain_water','fountain_jet'):
        found=[p for p in refs if p.stem.endswith('_'+paint)]
        assert len(found)==1,(paint,found)
        targets[found[0]]={paint.encode()}
    manifest={'revision':'fountain-water-v3','stage_revision':args.revision,'files':{},'geometry':{},
              'source_sha256':{},'protected_sha256':{},'streams':4,'impact_droplets':128,
              'breakup_beads':32,'splash_fingers':32,'scene_changed':False,'physics_changed':False,
              'lion_lily_bell_changed':False,'gpu_animation_only':True}

    def record(path,staged):
        relative=path.relative_to(ROOT).as_posix(); before=sha(path) if path.exists() else None
        backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(path,backup); assert sha(backup)==before
        manifest['files'][relative]={'source':staged.relative_to(ROOT).as_posix(),'before':before,'after':sha(staged),
                                    'backup':backup.relative_to(ROOT).as_posix() if before else None}

    for path,paints in targets.items():
        before=sha(path); target=stage/path.relative_to(ROOT)
        report=replace_water(path,piece,target,paints)
        assert sha(path)==before
        assert set(report['removed_triangles'])=={p.decode() for p in paints}
        manifest['geometry'][path.relative_to(ROOT).as_posix()]=report
        record(path,target)
    for name,text in W.material_definitions().items():
        relative=Path(f'Assets/materials/belltower/{name}.vmat')
        target=stage/relative; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text)
        record(ROOT/relative,target)
    for name in ('surface','stream'):
        filename=f'belltower_fountain_{name}_v3.shader'
        path=ROOT/'Assets/shaders'/filename; target=stage/path.relative_to(ROOT)
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/'Sources/Belltower/shaders'/filename,target); record(path,target)
    for path in [vmdl,vmdl.with_suffix('.mtl'),ROOT/'Assets/scenes/maps/Belltower/belltower.scene',
                 *[p for p in refs if p not in targets],
                 ROOT/'Assets/materials/belltower/fountain_water_normal.png',
                 ROOT/'Assets/materials/belltower/fountain_jet_normal.png']:
        manifest['protected_sha256'][path.relative_to(ROOT).as_posix()]=sha(path)
    for p in ['Tools/belltower_fountain_water.py','Tools/belltower_stage_fountain_water_v3.py',
              'Sources/Belltower/shaders/belltower_fountain_surface_v3.shader',
              'Sources/Belltower/shaders/belltower_fountain_stream_v3.shader']:
        manifest['source_sha256'][p]=sha(ROOT/p)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'stage':str(stage),'files':len(manifest['files']),'geometry':manifest['geometry'],
                      'protected_files':len(manifest['protected_sha256'])}))


if __name__=='__main__': main()
