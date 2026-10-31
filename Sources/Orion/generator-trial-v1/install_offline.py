"""Publish the approved generator offline; preserve all other scene data and packed collision."""
from pathlib import Path
import copy,hashlib,json,re,shutil,uuid
ROOT=Path.cwd();assert (ROOT/'hc1.sbproj').exists();HERE=ROOT/'Sources/Orion/generator-trial-v1'
OUT=ROOT/'output/orion-generator-installed-20261030';STAGE=OUT/'stage/Assets';manifest=json.loads((OUT/'manifest.json').read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
scene=ROOT/'Assets'/manifest['sceneRelative'];assert sha(scene)==manifest['sceneSHA256'],'Scene changed since staging'
collision=ROOT/'Assets/models/maps/orion/orion_launch_deck.vmdl'
assert sha(collision)==manifest['originalCollisionModelSHA256'],'Packed collision model changed'
for f in manifest['files']:
    rel=f['relative'];assert '..' not in Path(rel).parts
    assert rel.startswith(('models/props/orion/generator_v1/','materials/orion/generator_v1/')) or rel=='models/maps/orion/orion_launch_deck.obj'
    assert sha(ROOT/'Assets'/rel)==f['before'],('Target changed',rel)
    assert sha(STAGE/rel)==f['after'],('Stage changed',rel)
# Reuse the engine-serialized schema from the accepted reel, with new stable IDs.
instance=json.loads((ROOT/'Sources/Orion/cable-reel-trial-v1/native-instance.json').read_text())
namespace=uuid.UUID('56775925-3ac4-4848-bd6a-fb1e37711ee8')
guid=lambda name:str(uuid.uuid5(namespace,name))
instance.update({'__guid':guid('orion/generator/instance'),'Name':'ORION standby generator','Position':'1335,-265,240'})
assert len(instance['Components'])==1 and not instance['Children']
renderer=instance['Components'][0];assert renderer['__type']=='Sandbox.ModelRenderer'
renderer['__guid']=guid('orion/generator/renderer');model_guid=guid(manifest['resource'])
renderer['Model']={'Id':model_guid,'Path':manifest['resource']}
assert instance['Rotation']=='0,0,0,1' and instance['Scale']=='1,1,1' and renderer['Tint']=='1,1,1,1'
text=scene.read_bytes().decode('utf-8');original=json.loads(text);parent=next(n for n in original['GameObjects'] if n.get('Name')=='Orion')
assert not any(n.get('Name')==instance['Name'] for n in parent['Children'])
assert parent['Position']=='0,0,0' and parent['Rotation']=='0,0,0,1' and parent['Scale']=='1,1,1'
decoder=json.JSONDecoder();array=re.search(r'"GameObjects"\s*:\s*\[',text);assert array
i=array.end();parent_start=parent_end=None
while i<len(text):
    while text[i].isspace() or text[i]==',':i+=1
    if text[i]==']':break
    node,end=decoder.raw_decode(text,i)
    if node.get('Name')=='Orion':parent_start,parent_end=i,end;break
    i=end
assert parent_start is not None
parent_text=text[parent_start:parent_end];children=re.search(r'"Children"\s*:\s*\[',parent_text);assert children
child_start=parent_start+children.end()-1;child_array,end=decoder.raw_decode(text,child_start);assert child_array==parent['Children']
addition=(',\n' if child_array else '\n')+json.dumps(instance,indent=2)+'\n';updated=text[:end-1]+addition+text[end-1:]
expected=copy.deepcopy(original);next(n for n in expected['GameObjects'] if n.get('Name')=='Orion')['Children'].append(instance)
assert json.loads(updated)==expected,'Scene insertion changed unrelated data'
# Make the model's offline GUID agree with the reference in the saved scene.
meta_rel=manifest['resource']+'.meta';meta=ROOT/'Assets'/meta_rel;assert not meta.exists()
payloads=[(f['relative'],(STAGE/f['relative']).read_bytes()) for f in manifest['files']]
payloads += [(meta_rel,(json.dumps({'guid':model_guid},indent=2)+'\n').encode()),(manifest['sceneRelative'],updated.encode())]
completed=[];created=[]
try:
    for rel,data in payloads:
        target=ROOT/'Assets'/rel;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():
            backup=OUT/'before'/rel;backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();shutil.copy2(target,backup)
        else:created.append(rel)
        incoming=target.with_name(target.name+'.generator-incoming');incoming.write_bytes(data);incoming.replace(target);completed.append(rel)
    (HERE/'native-instance.json').write_text(json.dumps(instance,indent=2))
except BaseException:
    for rel in reversed(completed):
        target=ROOT/'Assets'/rel
        if rel in created:target.unlink()
        else:shutil.copy2(OUT/'before'/rel,target)
    raise
assert sha(collision)==manifest['originalCollisionModelSHA256']
receipt={'installedInSavedAssets':True,'mode':'offline at user request','nativeCompilationAndRenderingPerformed':False,
 'model':manifest['resource'],'modelGuid':model_guid,'worldPosition':[1335,-265,240],'removedPlaceholderTriangles':12,
 'collisionUnchanged':True,'otherSceneDataUnchanged':True,'instanceSchema':'Cloned from the engine-serialized accepted reel; new instance/component/model GUIDs',
 'lodTriangles':manifest['lodTriangles'],'sceneBeforeSHA256':manifest['sceneSHA256'],'sceneAfterSHA256':sha(scene),
 'approvedPreviewGLBSHA256':manifest['sourcePreviewGLBSHA256'],'installedFiles':{rel:sha(ROOT/'Assets'/rel) for rel,_ in payloads}}
(OUT/'offline-install.json').write_text(json.dumps(receipt,indent=2));print(json.dumps({k:v for k,v in receipt.items() if k!='installedFiles'},indent=2))
