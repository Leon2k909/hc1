import hashlib,json,math
from pathlib import Path
STAGE=Path(__file__).resolve().parent
ROOT=STAGE.parents[2]
BEFORE=STAGE.parent/'flood-lighting-before-20261020'
SCENE=ROOT/'Assets/scenes/maps/forestbase/forestbase.scene'
def nodes(scene):
    result={}
    def walk(items,parent=None):
        for n in items:
            result[n['__guid']]=({k:v for k,v in n.items() if k!='Children'},parent,[c['__guid'] for c in n.get('Children',[])])
            walk(n.get('Children',[]),n['__guid'])
    walk(scene['GameObjects']);return result
def vec(s):return tuple(map(float,s.split(',')))
old_scene=json.loads((BEFORE/'Assets/scenes/maps/forestbase/forestbase.scene').read_text())
new_scene=json.loads(SCENE.read_text())
old,new=nodes(old_scene),nodes(new_scene)
assert old.keys()==new.keys()
assert {k:v for k,v in old_scene.items() if k!='GameObjects'}=={k:v for k,v in new_scene.items() if k!='GameObjects'}
plans={n['__guid']:n for n in json.loads((STAGE/'lights.json').read_text())}
global_fields={'Cool Daylight':{'LightColor','SkyColor'},'Sky':{'Tint'},'Forest Mist':{'Color'}}
changed=[];position_errors=[];rotation_errors=[]
for guid,(a,parent,children) in old.items():
    b,p,c=new[guid]
    assert parent==p and children==c
    if a==b:continue
    name=a.get('Name','')
    assert guid in plans or name in global_fields,name
    aa=json.loads(json.dumps(a));bb=json.loads(json.dumps(b))
    if guid in plans:
        plan=plans[guid];component=plan['Components'][0]
        bc=bb['Components'][0];ac=aa['Components'][0]
        assert max(abs(x-y) for x,y in zip(vec(bc['LightColor']),vec(component['LightColor'])))<.00001
        ac.pop('LightColor');bc.pop('LightColor')
        if name.startswith('Flood '):
            position_errors.append(max(abs(x-y) for x,y in zip(vec(bb['Position']),vec(plan['Position']))))
            aq,bq=vec(bb['Rotation']),vec(plan['Rotation'])
            rotation_errors.append(min(max(abs(x-y) for x,y in zip(aq,bq)),max(abs(x+y) for x,y in zip(aq,bq))))
            assert ac.pop('Radius')==760 and bc.pop('Radius')==950
            for n in (aa,bb):n.pop('Position');n.pop('Rotation')
    else:
        for key in global_fields[name]:
            aa['Components'][0].pop(key);bb['Components'][0].pop(key)
    assert aa==bb,name
    changed.append(name)
assert len(changed)==39 and len(position_errors)==11
assert max(position_errors)<.002 and max(rotation_errors)<.00001
source=json.loads((STAGE/'source-audit.json').read_text())
for ext in ('obj','mtl','vmdl'):
    assert (ROOT/f'Assets/models/maps/forestbase/ground.{ext}').read_bytes()==(STAGE/f'models/maps/forestbase/ground.{ext}').read_bytes()
assert source['exactCollisionPreserved']
old_obj=(BEFORE/'Assets/models/maps/forestbase/ground.obj').read_text().splitlines()
new_obj=(ROOT/'Assets/models/maps/forestbase/ground.obj').read_text().splitlines()
assert len(old_obj)==len(new_obj)
vertex_changes=0;normal_changes=0;uv_changes=0
uv_index=0;changed_uvs=set();normal_index=0;changed_normals=set()
old_vertices=[tuple(map(float,line.split()[1:4])) for line in old_obj if line.startswith('v ')]
points=[vec(n['Position']) for n in plans.values() if n['Name'].startswith('Flood ')]
def near_head(vertex):
    west,z,north=vertex
    return min(math.dist((north,west,z),p) for p in points)<70
for a,b in zip(old_obj,new_obj):
    if a.startswith('vt '):uv_index+=1
    if a.startswith('vn '):normal_index+=1
    if a==b:continue
    assert a.startswith(('v ','vn ','vt ')) and a.split()[0]==b.split()[0]
    if a.startswith('v '):
        vertex_changes+=1
        # OBJ (west,up,north) -> native (north,west,up). All edited
        # vertices must be near one of the eleven existing lamp heads.
        assert near_head(tuple(map(float,a.split()[1:4])))
    elif a.startswith('vn '):
        normal_changes+=1;changed_normals.add(normal_index)
    else:
        uv_changes+=1;changed_uvs.add(uv_index)
# World-projected UVs and face normals rotate with the same existing heads.
# The topology is identical; no changed coordinate may affect another mesh.
for line in old_obj:
    if not line.startswith('f '):continue
    face=[tuple(map(int,item.split('/'))) for item in line.split()[1:]]
    if any(t in changed_uvs or n in changed_normals for v,t,n in face):
        assert all(near_head(old_vertices[v-1]) for v,t,n in face)
report=dict(changedNodes=len(changed),changedNodeNames=changed,lightCount=len(plans),reaimedFloods=11,
            allOtherSceneContentUnchanged=True,existingHeadVertexChanges=vertex_changes,existingHeadNormalChanges=normal_changes,existingHeadUvChanges=uv_changes,
            exactCollisionPreserved=True,ground=source['ground'],maximumGeneratorPositionErrorInches=max(position_errors),
            maximumGeneratorQuaternionError=max(rotation_errors),sceneSha256=hashlib.sha256(SCENE.read_bytes()).hexdigest(),
            scope='Scene identity, source geometry and light generator parity. Does not prove final match performance or remote-client playability.')
(STAGE/'installed-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
