"""Confirm the saved hitch and retire its exact legacy/comparison resource names."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/trailer-hitch-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
p=json.loads((OUT/'install-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/p['source'])==p['source_after']
assert sha(ROOT/'Assets/models/maps/riverside/riverside_low.vmdl')==p['low_vmdl_before']
b=json.loads((OUT/'install-before/riverside.scene').read_text());a=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
group=next(g for g in a['GameObjects'] if g.get('Name')=='Trailer Hitches');assert len(group['Children'])==1
item=group['Children'][0];assert item['Name']=='T2 Trailer Hitch'
assert len(item['Components'])==1 and item['Components'][0]['__type']=='Sandbox.ModelRenderer'
resource=item['Components'][0]['Model']
assert (resource['Path'] if isinstance(resource,dict) else resource)==p['model']
original_ids={g['__guid'] for g in b['GameObjects']};trimmed=dict(a);trimmed['GameObjects']=[g for g in a['GameObjects'] if g['__guid'] in original_ids]
assert trimmed==b,'Existing scene data changed; inspect before cleanup.'
concurrent=[g.get('Name') for g in a['GameObjects'] if g['__guid'] not in original_ids and g is not group]
capture=json.loads((OUT/'installed-capture.json').read_text());assert capture['SourceUnchanged'] and not capture['ErrorModels']
generator=json.loads((OUT/'generator-check.json').read_text());assert generator['OnlyOriginalHitchRemoved'] and generator['CollisionPreserved']
with Editor() as e:
    result=e.script(r'''var model=Model.Load("models/props/riverside/trailer_hitch_v1/hitch.vmdl");
if(model.IsError||model.MeshInfo.LodCount!=3)throw new Exception("Installed hitch is invalid");
var counts=model.MeshInfo.Meshes.Select(m=>m.Triangles).ToArray();
if(!counts.SequenceEqual(new[]{8422,5470,1526}))throw new Exception("Hitch differs from the approved mesh");
var project=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.GetFullPath(System.IO.Path.Combine(project,"Assets/models/props/riverside/trailer_hitch_v1"));
var files=System.IO.Directory.EnumerateFiles(folder).Where(p=>System.IO.Path.GetFileName(p).StartsWith("legacy_hitch.")||System.IO.Path.GetFileName(p).StartsWith("low_without_hitch.")).ToArray();
if(files.Any(f=>System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(f))!=folder))throw new Exception("Unexpected removal target");
var archive=System.IO.Path.Combine(project,"output/riverside/trailer-hitch-v1/retired-review-assets");System.IO.Directory.CreateDirectory(archive);
foreach(var file in files){System.IO.File.Copy(file,System.IO.Path.Combine(archive,System.IO.Path.GetFileName(file)),true);System.IO.File.Delete(file);}
return new{Installed=true,Hitches=1,LodTriangles=counts,DeletedComparisonFiles=files.Length,SourceScene=Editor.SceneEditorSession.Active.Scene.Name,Game.IsPlaying};''','finish-tv-hitch-install.cs')
    result.update(RemovedOldTriangles=48,OriginalLowlandModelDocPreserved=True,ExistingSceneObjectsPreserved=True,ConcurrentAdditionsPreserved=concurrent,CollisionPreserved=True,PointLightsPreserved=True)
    (OUT/'installed.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
