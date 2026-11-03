"""Refine only collision after the unchanged visual mesh has been rendered."""
import importlib.util,json
from pathlib import Path

HERE=Path(__file__).parent
spec=importlib.util.spec_from_file_location('cabinet_builder',HERE/'build.py')
B=importlib.util.module_from_spec(spec);spec.loader.exec_module(B)
OUT=B.OUT/'collision-refinement'
assert not (OUT/'change.json').exists(),'Collision refinement already recorded'
report=json.loads((HERE/'candidate.json').read_text())
for p,h in report['protectedSourceSHA256'].items():assert B.sha(B.ROOT/p)==h,p
before={p:B.sha(B.DEST/p) for p in ('after.obj','after.vmdl','after_hulls_metal.obj','after_hulls_rubber.obj')}
mesh=B.candidate()
OUT.mkdir(parents=True,exist_ok=True)
check=OUT/'visual-check/after.obj';check.parent.mkdir(parents=True,exist_ok=True)
B.K.write_obj(check,mesh,'after')
assert B.sha(check)==before['after.obj'],'Collision refinement changed visible geometry'
for name in before:
    backup=OUT/'before'/name;backup.parent.mkdir(parents=True,exist_ok=True)
    backup.write_bytes((B.DEST/name).read_bytes())
B.K.write_vmdl(B.DEST/'after.vmdl',B.RESOURCE,'after',mesh)
old=(OUT/'before/after.vmdl').read_text();new=(B.DEST/'after.vmdl').read_text()
marker='\t\t\t{\n\t\t\t\t_class = "PhysicsShapeList"'
assert old.split(marker)[0]==new.split(marker)[0],'Render mesh or material bindings changed'
assert B.sha(B.DEST/'after.obj')==before['after.obj']
records={}
for name,h in before.items():
    path=B.DEST/name;current=B.sha(path)
    if current!=h:records[path.relative_to(B.ROOT).as_posix()]={'before':h,'after':current,'backup':(OUT/'before'/name).relative_to(B.ROOT).as_posix()}
assert set(Path(p).name for p in records)=={'after.vmdl','after_hulls_metal.obj'}
report['models']['after'].update(boxes=len(mesh.boxes),hulls=len(mesh.hulls))
report['collisionShapes']=B.SHAPES;report['wheels']=B.WHEELS
report['collisionDesign']='Rounded cabinet/worktop and tyre/pivot hulls; individual drawer faces, forks, plates and grips; open underside'
for p in (HERE/'candidate.json',B.OUT/'manifest.json'):p.write_text(json.dumps(report,indent=2)+'\n')
proof={'collisionOnly':True,'visibleOBJUnchanged':before['after.obj'],'renderMeshAndMaterialBindingsUnchanged':True,
       'changedFiles':records,'boxes':len(mesh.boxes),'hulls':len(mesh.hulls),'installedInMap':False}
(OUT/'change.json').write_text(json.dumps(proof,indent=2)+'\n')
print(json.dumps(proof))
