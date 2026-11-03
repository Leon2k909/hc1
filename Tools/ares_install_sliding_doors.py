"""Install two automatic sliding doors offline, preserving the current Ares scene."""
from pathlib import Path
import hashlib,json,math,re,shutil,sys,uuid
ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'Tools'))
OUT=ROOT/'output/ares/sliding-doors-20261031';OUT.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'Sources/Ares/sliding-doors-v1';SRC.mkdir(parents=True,exist_ok=True)
base=ROOT/'Assets/models/maps/collider/automatic-door-v1';dest=ROOT/'Assets/models/maps/ares/sliding-doors-v1'
scene=ROOT/'Assets/scenes/maps/Ares/ares.scene';generator=ROOT/'Tools/ares_map.py';collider=ROOT/'Assets/scenes/maps/Collider/collider.scene'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
original_scene=scene.read_bytes();scene_hash=sha(scene);original_generator=generator.read_text();generator_hash=sha(generator)
template_scene=json.loads(collider.read_text());template=next(x for x in template_scene['GameObjects'] if x.get('Name')=='Automatic west lab door')
assert len(template['Children'])==2 and any(c['__type']=='Facepunch.AutomaticSlidingDoor' for c in template['Components'])
assert not (SRC/'collider-door-template.json').exists() and not dest.exists()
assert 'ares_sliding_doors' not in original_generator
base_obj=base/'lab_door_leaf.obj';base_doc=base/'lab_door_leaf.vmdl';base_mtl=base/'lab_door_leaf.mtl'
source_hash={str(p.relative_to(ROOT)):sha(p) for p in (base_obj,base_doc,base_mtl,collider,ROOT/'Code/World/AutomaticSlidingDoor.cs')}
factor=1.28;height_factor=172/188
lines=[]
for line in base_obj.read_text().splitlines():
    p=line.split()
    if not p:lines.append(line);continue
    if p[0]=='v':x,y,z=map(float,p[1:]);line=f'v {x*factor:.7f} {y*height_factor:.7f} {z:.7f}'
    elif p[0]=='vn':
        x,y,z=map(float,p[1:]);x/=factor;y/=height_factor;length=math.sqrt(x*x+y*y+z*z);assert length>0
        line=f'vn {x/length:.9f} {y/length:.9f} {z/length:.9f}'
    elif p[0]=='mtllib':line='mtllib ares_sliding_leaf.mtl'
    elif p[0]=='o':line='o ares_sliding_leaf'
    lines.append(line)
doc=base_doc.read_text().replace('models/maps/collider/automatic-door-v1/lab_door_leaf.obj','models/maps/ares/sliding-doors-v1/ares_sliding_leaf.obj').replace('name = "lab_door_leaf"','name = "ares_sliding_leaf"')
before='dimensions = [ 88.2000, 8.0000, 188.0000 ]';after='dimensions = [ 112.8960, 8.0000, 172.0000 ]';assert doc.count(before)==1;doc=doc.replace(before,after)
for path in re.findall(r'to = "([^"]+)"',doc):assert (ROOT/'Assets'/path).exists(),path
guid=str(uuid.uuid5(uuid.UUID('cf436d94-97ff-46af-af20-432a9e5a8b9a'),'ares-sliding-leaf-model'))
payloads={dest/'ares_sliding_leaf.obj':('\n'.join(lines)+'\n').encode(),dest/'ares_sliding_leaf.mtl':base_mtl.read_bytes(),
 dest/'ares_sliding_leaf.vmdl':doc.encode(),dest/'ares_sliding_leaf.vmdl.meta':(json.dumps({'guid':guid},indent=2)+'\n').encode(),
 SRC/'collider-door-template.json':(json.dumps(template,indent=2)+'\n').encode()}
for p in payloads:assert not p.exists(),p
# New helper reads the template and model meta; write those two private inputs first.
for path in (SRC/'collider-door-template.json',dest/'ares_sliding_leaf.vmdl.meta'):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(payloads[path])
try:
    import ares_sliding_doors as doors
    objects=doors.scene_objects();assert len(objects)==2
    data=json.loads(original_scene);existing={x.get('Name') for x in data['GameObjects']}
    assert not any(x['Name'] in existing for x in objects)
    text=original_scene.decode();marker=re.search(r'"GameObjects"\s*:\s*\[',text);assert marker
    arr,end=json.JSONDecoder().raw_decode(text,marker.end()-1);assert arr==data['GameObjects']
    inserted=',\n'+',\n'.join(json.dumps(x,indent=2) for x in objects)+'\n';updated=text[:end-1]+inserted+text[end-1:]
    expected=json.loads(original_scene);expected['GameObjects'].extend(objects);assert json.loads(updated)==expected
    anchor='    scene = {\n        "__guid": ids( "scene" ),';assert original_generator.count(anchor)==1
    new_generator=original_generator.replace(anchor,'    from ares_sliding_doors import scene_objects as automatic_door_objects\n    objects.extend( automatic_door_objects() )\n\n'+anchor)
    assert sha(scene)==scene_hash and sha(generator)==generator_hash
    for p,h in source_hash.items():assert sha(ROOT/p)==h,p
    for path,data in payloads.items():
        if path in (SRC/'collider-door-template.json',dest/'ares_sliding_leaf.vmdl.meta'):continue
        path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
    for path in (scene,generator):
        backup=OUT/'before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();shutil.copy2(path,backup)
    for path,data in ((scene,updated.encode()),(generator,new_generator.encode())):
        tmp=path.with_name(path.name+'.automatic-door-incoming');tmp.write_bytes(data);tmp.replace(path)
except BaseException:
    for path in (scene,generator):
        backup=OUT/'before'/path.relative_to(ROOT)
        if backup.exists():shutil.copy2(backup,path)
    for path in payloads:
        if path.exists():path.unlink()
    raise
receipt={'doors':2,'openingWidth':224,'openingHeight':176,'leafWidth':112,'leafHeight':172,'travel':114,
 'worldPositions':[[0,1116,0],[0,-1116,0]],'component':'Facepunch.AutomaticSlidingDoor','sourceColliderSceneAndModelUnchanged':True,
 'sceneDataOnlyAddsTwoDoors':True,'compiledOrPlaytested':False,'beforeSceneSHA256':scene_hash,
 'afterSceneSHA256':sha(scene),'generatorSHA256':sha(generator),'model':doors.MODEL,'assetGUID':guid,'sourceSHA256':source_hash}
(OUT/'installation.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
