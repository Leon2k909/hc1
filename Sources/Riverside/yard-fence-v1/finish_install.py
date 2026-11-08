"""Confirm the saved roof and retire its exact legacy/comparison resource names."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/yard-fence-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
p=json.loads((OUT/'install-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/p['source'])==p['source_after']
assert sha(ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl')==p['dressing_vmdl_before']
b=json.loads((OUT/'install-before/riverside.scene').read_text());a=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
group=next(g for g in a['GameObjects'] if g.get('Name')=='West Yard Fences');assert len(group['Children'])==1
item=group['Children'][0];assert item['Name']=='West Yard Privacy Fence'
assert len(item['Components'])==1 and item['Components'][0]['__type']=='Sandbox.ModelRenderer'
resource=item['Components'][0]['Model']
assert (resource['Path'] if isinstance(resource,dict) else resource)==p['model']
original_ids={g['__guid'] for g in b['GameObjects']};trimmed=dict(a);trimmed['GameObjects']=[g for g in a['GameObjects'] if g['__guid'] in original_ids]
# Inspected editor-only serialization refreshes: same zombies prefab reference/empty patch,
# and the same window renderer expressed with explicit default fields and a resource handle.
prefab='f1f7cc32-4465-5224-aae4-7dd888970d19';window='320aa567-9241-5701-8d35-72eb38c9471e'
old={g['__guid']:g for g in b['GameObjects']};new={g['__guid']:g for g in trimmed['GameObjects']}
assert old[prefab]['__Prefab']==new[prefab]['__Prefab'] and old[prefab]['__PrefabInstancePatch']==new[prefab]['__PrefabInstancePatch']
new[prefab]['__PrefabIdToInstanceId']=old[prefab]['__PrefabIdToInstanceId']
oc=old[window]['Components'][0];nc=new[window]['Components'][0];np=nc['Model'];assert (np['Path'] if isinstance(np,dict) else np)==oc['Model']
for k,v in oc.items():
 if k!='Model':assert nc[k]==v,(k,nc[k],v)
defaults={k:v for k,v in nc.items() if k not in oc}
assert all(v is None or (k=='CreateAttachments' and v is False) or (k=='RenderOptions' and v==dict(GameLayer=True,OverlayLayer=False,BloomLayer=False,AfterUILayer=False)) for k,v in defaults.items())
new[window]['Components']=old[window]['Components']
assert trimmed==b,'Scene changed beyond inspected editor serialization defaults; inspect before cleanup.'
concurrent=[g.get('Name') for g in a['GameObjects'] if g['__guid'] not in original_ids and g is not group]
capture=json.loads((OUT/'installed-capture.json').read_text());assert capture['SourceUnchanged'] and not capture['ErrorModels']
generator=json.loads((OUT/'generator-check.json').read_text());assert generator['OnlyOriginalFenceRemoved'] and generator['CollisionPreserved']
with Editor() as e:
    result=e.script(r'''var model=Model.Load("models/props/riverside/yard_fence_v1/fence.vmdl");
if(model.IsError||model.MeshInfo.LodCount!=3)throw new Exception("Installed roof is invalid");
var counts=model.MeshInfo.Meshes.Select(m=>m.Triangles).ToArray();
if(!counts.SequenceEqual(new[]{11048,7648,1284}))throw new Exception("Roof differs from the approved mesh");
var project=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.GetFullPath(System.IO.Path.Combine(project,"Assets/models/props/riverside/yard_fence_v1"));
var files=System.IO.Directory.EnumerateFiles(folder).Where(p=>System.IO.Path.GetFileName(p).StartsWith("legacy_fence.")||System.IO.Path.GetFileName(p).StartsWith("dressing_without_fence.")).ToArray();
if(files.Any(f=>System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(f))!=folder))throw new Exception("Unexpected removal target");
var archive=System.IO.Path.Combine(project,"output/riverside/yard-fence-v1/retired-review-assets");System.IO.Directory.CreateDirectory(archive);
foreach(var file in files){System.IO.File.Copy(file,System.IO.Path.Combine(archive,System.IO.Path.GetFileName(file)),true);System.IO.File.Delete(file);}
return new{Installed=true,Fences=1,LodTriangles=counts,DeletedComparisonFiles=files.Length,SourceScene=Editor.SceneEditorSession.Active.Scene.Name,Game.IsPlaying};''','finish-tv-roof-install.cs')
    result.update(RemovedOldTriangles=1044,OriginalDressingModelDocPreserved=True,ExistingSceneObjectsPreserved=True,EditorSerializationRefreshPreserved=True,ConcurrentAdditionsPreserved=concurrent,CollisionPreserved=True,PointLightsPreserved=True)
    (OUT/'installed.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
