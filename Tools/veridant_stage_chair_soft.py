"""Stage only the two dedicated chair imports and their own material bindings."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil

import numpy as np

import map_kit as K
import veridant_chair_soft as C
from belltower_compact_obj import compact
from belltower_safe_imports import span
from veridant_stage_chairs import placements

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/chair-v4'
STAGE=OUT/'stage-v4'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def setup_capture():
    OUT.mkdir(parents=True,exist_ok=True)
    STAGE.mkdir(parents=True,exist_ok=True)
    rows=[{'at':at.tolist(),'facing':f.tolist(),'z0':z} for at,f,z in placements()]
    (OUT/'capture-manifest.json').write_text(json.dumps({'placements':rows},indent=2)+'\n')
    source=(ROOT/'Sources/Veridant/chair-v3/capture.cs.txt').read_text()
    source=source.replace('output/veridant/chair-v3','output/veridant/chair-v4')
    source=source.replace('config["stage"].GetValue<string>(), "manifest.json"','"capture-manifest.json"')
    source=re.sub(r'new\[\] \{ \(Index:0, Name:"front-close".*?Target:17.2f\) \}',
        'new[] { (Index:8, Name:"chair", Forward:30f, Side:26f, Height:36f, Target:17f),\n'
        '    (Index:8, Name:"front", Forward:24f, Side:-30f, Height:33f, Target:18f),\n'
        '    (Index:8, Name:"side", Forward:0f, Side:39f, Height:30f, Target:17f),\n'
        '    (Index:8, Name:"rear", Forward:-31f, Side:23f, Height:34f, Target:18f),\n'
        '    (Index:0, Name:"terrace", Forward:38f, Side:36f, Height:39f, Target:17f) }',source,flags=re.S)
    destination=ROOT/'Sources/Veridant/chair-v4'
    destination.mkdir(parents=True,exist_ok=True)
    source=source.replace('return new { Files=files,',
        'return new { Files=files, Stage="stage-v4", ModelIsError=Model.Load("models/maps/veridant/veridant_dress.vmdl").IsError,')
    (destination/'capture.cs.txt').write_text(source,encoding='utf-8')
    (OUT/'capture-request.json').write_text(json.dumps({'phase':'before','stage':'stage-v1'}))


def main():
    assert not (STAGE/'manifest.json').exists(),'Preserve the staged revision'
    STAGE.mkdir(parents=True,exist_ok=True)
    vmdl=Path('Assets/models/maps/veridant/veridant_dress.vmdl')
    document=(ROOT/vmdl).read_text()
    original=document
    before_hash=sha(ROOT/vmdl)
    a,b=span(document,'_class = "RenderMeshList"')
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',document[a:b])
    old_imports=[p for p in imports if re.fullmatch(r'models/maps/veridant/chair-v[34]/chairs-[01]\.obj',p)]
    assert len(old_imports)==2 and len(set(old_imports))==2
    assert all(imports.count(p)==1 for p in old_imports),'Inspect the current chair imports'
    protected_paths=[ROOT/'Assets'/p for p in imports if '/chair-v4/' not in p]
    protected_paths += [ROOT/'Assets/models/maps/veridant/veridant_dress.obj',
                        ROOT/'Assets/scenes/maps/Veridant/veridant.scene',
                        ROOT/'Tools/veridant_chair_soft.py',ROOT/'Tools/veridant_chair.py']
    protected={p.relative_to(ROOT).as_posix():sha(p) for p in protected_paths}
    paths=[]; chunks=[]; triangle_counts=[]; geometry=[]
    rows=placements()
    for start in range(0,len(rows),6):
        model=K.Model()
        for index,(at,f,z0) in enumerate(rows[start:start+6],start):
            single=K.Model(); C.build_into(single,at,f,z0)
            points=np.array([p for faces in single.polygons.values() for pts,n in faces for p in pts])
            normals=np.array([n for values in single.polygon_normals.values() for n in values])
            assert np.isfinite(points).all() and np.isfinite(normals).all()
            assert np.allclose(np.linalg.norm(normals,axis=1),1)
            assert not single.boxes and not single.hulls
            assert abs(points[:,2].min()-z0)<1e-6
            assert 32.8<points[:,2].max()-z0<33.5
            model.extend(single)
            triangle_counts.append(single.triangle_count())
            geometry.append({'index':index,'triangles':single.triangle_count(),
                             'bounds':[points.min(0).tolist(),points.max(0).tolist()]})
            print(json.dumps({'chair':index+1,'triangles':single.triangle_count()}),flush=True)
        relative=Path(f'Assets/models/maps/veridant/chair-v4/chairs-{start//6}.obj')
        raw=STAGE/'raw'/relative
        raw.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(raw,model,raw.stem)
        target=STAGE/relative
        report=compact(raw,target,True)
        assert max(report['after_entries'].values())<65536,report['after_entries']
        shutil.copyfile(raw.with_suffix('.mtl'),target.with_suffix('.mtl'))
        paths.extend([relative,relative.with_suffix('.mtl')]); chunks.append(report)
        document=document.replace(old_imports[start//6],relative.relative_to('Assets').as_posix())
    material_dir=Path('Assets/materials/veridant/chair-v4')
    C.write_materials(STAGE/material_dir)
    for material in (STAGE/material_dir).glob('*.vmat'): paths.append(material.relative_to(STAGE))
    a,b=span(document,'_class = "DefaultMaterialGroup"')
    at=document.index('remaps =',a,b)
    bracket=document.index('[',at,b)+1
    remaps=''.join(f'{{ from = "{name}.vmat" to = "{path}" }},\n'
                       for name,path in C.MATERIALS.items()
                       if name.startswith('vr_chair_') and f'from = "{name}.vmat"' not in document)
    if remaps: document=document[:bracket]+'\n'+remaps+document[bracket:]
    a,b=span(original,'_class = "PhysicsShapeList"')
    c,d=span(document,'_class = "PhysicsShapeList"')
    assert original[a:]==document[c:],'Preserve all physics and subsequent document bytes'
    (STAGE/vmdl).parent.mkdir(parents=True,exist_ok=True)
    (STAGE/vmdl).write_text(document)
    if document!=original: paths.append(vmdl)
    else:
        # This pass writes only our own leaf assets. Other prop jobs can update
        # the shared model/base while these leaves are being built.
        protected={p:value for p,value in protected.items() if p.startswith('Tools/veridant_chair')}
    files={}
    for relative in paths:
        target=ROOT/relative
        old=sha(target) if target.exists() else None
        if old:
            backup=STAGE/'before'/relative
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,backup)
        files[relative.as_posix()]={'before':old,'after':sha(STAGE/relative),
                                  'source':(STAGE/relative).relative_to(ROOT).as_posix()}
    assert sha(ROOT/vmdl)==before_hash
    assert all(sha(ROOT/p)==value for p,value in protected.items())
    manifest={'revision':'veridant-chair-soft-v4','files':files,'protected':protected,
              'instances':len(rows),'triangles_per_chair':triangle_counts,
              'geometry':geometry,'compaction':chunks,'physics_suffix_exact':True,
              'unrelated_imports_exact':True,'canonical_obj_unchanged':True}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'instances':len(rows),'triangles':sum(triangle_counts),
                      'files':len(files),'physics_unchanged':True}),flush=True)


if __name__=='__main__':
    import sys
    if '--setup' in sys.argv: setup_capture()
    else: main()
