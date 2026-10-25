import sys,json,hashlib
from pathlib import Path
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[3]
STAGE=Path(__file__).resolve().parent
BEFORE=STAGE.parent/'impact-mist-before-20261020'
sys.path.insert(0,str(ROOT/'Tools'))
import forestbase_map as M
def nodes(scene):
    result={}
    def walk(items,parent=None):
        for n in items:
            result[n['__guid']]=({k:v for k,v in n.items() if k!='Children'},parent,[c['__guid'] for c in n.get('Children',[])])
            walk(n.get('Children',[]),n['__guid'])
    walk(scene['GameObjects']);return result
scene_path=ROOT/'Assets/scenes/maps/forestbase/forestbase.scene'
old_scene=json.loads((BEFORE/'forestbase.scene').read_text())
new_scene=json.loads(scene_path.read_text())
old,new=nodes(old_scene),nodes(new_scene)
assert old.keys()==new.keys()
assert {k:v for k,v in old_scene.items() if k!='GameObjects'}=={k:v for k,v in new_scene.items() if k!='GameObjects'}
changed=[]
for guid,(a,parent,children) in old.items():
    b,p,c=new[guid];assert parent==p and children==c
    if a==b:continue
    assert a.get('Name','').startswith('Shore grass '),a.get('Name')
    aa=dict(a);bb=dict(b);aa.pop('Position');bb.pop('Position');assert aa==bb
    changed.append(a['Name'])
assert len(changed)==24
for ext in ('mtl','vmdl'):
    assert (ROOT/f'Assets/models/maps/forestbase/vista.{ext}').read_bytes()==(BEFORE/f'Assets/models/maps/forestbase/vista.{ext}').read_bytes()
assert (ROOT/'Assets/models/maps/forestbase/vista.obj').read_bytes()==(STAGE/'models/maps/forestbase/vista.obj').read_bytes()
def mesh_hashes(path):
    values=[[],[],[]];groups={};group=None;triangles=0
    for line in path.read_text().splitlines():
        tag=line.split(' ',1)[0]
        if tag in ('v','vt','vn'):values[('v','vt','vn').index(tag)].append(line)
        elif tag=='usemtl':group=line.split()[1];groups[group]=hashlib.sha256()
        elif tag=='f':
            triangles+=len(line.split())-3
            for item in line.split()[1:]:
                for axis,index in enumerate(map(int,item.split('/'))):groups[group].update((values[axis][index-1]+'\n').encode())
    return {name:h.hexdigest() for name,h in groups.items()},triangles
old_hashes,old_tri=mesh_hashes(BEFORE/'Assets/models/maps/forestbase/vista.obj')
new_hashes,new_tri=mesh_hashes(ROOT/'Assets/models/maps/forestbase/vista.obj')
assert old_hashes.keys()==new_hashes.keys()
changed_groups=[name for name in old_hashes if old_hashes[name]!=new_hashes[name]]
assert set(changed_groups)=={'forest_soil','mud','shore_bank','shore_rock'},changed_groups
assert new_tri==111666 and old_tri==111714
M.build(visual_chunks=[])
saved_forest=next(n for n in new_scene['GameObjects'] if n.get('Name')=='Forest Backdrop')['Children']
assert len(saved_forest)==len(M.INSTANCES)
def vec(s):return np.array(list(map(float,s.split(','))))
errors=[]
for node,(name,path,pos,yaw,scale) in zip(saved_forest,M.INSTANCES):
    assert node['Name']==name
    component=node['Components'][0];model=component['Model']
    assert (model['Path'] if isinstance(model,dict) else model)==path
    errors.append(float(np.max(np.abs(vec(node['Position'])-M.K.to_world(pos)))))
    assert np.max(np.abs(vec(node['Scale'])-scale))<.001
assert max(errors)<.02
layout=json.loads((ROOT/'output/forestbase/layout.json').read_text())
old_layout=json.loads((BEFORE/'output/forestbase/layout.json').read_text())
assert layout['stats']['vista']['triangles']==new_tri
layout['stats']['vista']['triangles']=old_tri
assert layout==old_layout
contact=json.loads((STAGE/'shore-contact-audit.json').read_text())
assert contact['poolEdgeSamples']==96 and contact['minimumBankOverlapInches']>1 and contact['poolContourUnchanged']
imgs={name:np.asarray(Image.open(STAGE/f'probe-{name}.png').convert('RGB')).astype(float) for name in ('motion0','motion1','soft10','hard10')}
motion=np.abs(imgs['motion1']-imgs['motion0']).max(axis=2)
assert np.count_nonzero(motion>2)>500
soft=imgs['soft10'][160:480,160:480].mean();hard=imgs['hard10'][160:480,160:480].mean()
assert soft<hard
report=dict(sceneNodes=len(new),changedGrass=changed,allOtherSceneContentUnchanged=True,
            vistaTrianglesBefore=old_tri,vistaTrianglesAfter=new_tri,changedGeometryMaterials=changed_groups,
            unchangedGeometryMaterials=len(old_hashes)-len(changed_groups),vistaModelDocAndCollisionUnchanged=True,
            materialSlots=len(new_hashes),generatorInstances=len(errors),maximumGeneratorPositionErrorInches=max(errors),
            poolEdge=contact,mistProbe=dict(changedMotionPixelsOver2=int(np.count_nonzero(motion>2)),softPatchMean=soft,hardPatchMean=hard,
                scope='Isolated installed mist shader on a plane over an existing valid rubber material; motion and softer depth intersection. Does not establish a fluid simulation or map FPS.'),
            sceneSha256=hashlib.sha256(scene_path.read_bytes()).hexdigest(),
            mistShaderSha256=hashlib.sha256((ROOT/'Assets/shaders/forestbase_mist.shader').read_bytes()).hexdigest())
(STAGE/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ('changedGrass','poolEdge')}))
