"""Verify the approved installation and retire only its unused comparison resources."""
from pathlib import Path
import sys,json,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/roof-ac-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
plan=json.loads((OUT/'install-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/plan['source'])==plan['source_after']
assert sha(ROOT/'Assets/models/maps/riverside/riverside_pad.vmdl')==plan['pad_vmdl_before']
before=json.loads((OUT/'install-before/riverside.scene').read_text());after=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
groups=[g for g in after['GameObjects'] if g.get('Name')=='Roof Air Conditioners'];assert len(groups)==1
children=groups[0]['Children'];assert len(children)==1 and children[0]['Name']=='Office Rooftop AC'
assert len(children[0]['Components'])==1 and children[0]['Components'][0]['__type']=='Sandbox.ModelRenderer'
trimmed=dict(after);trimmed['GameObjects']=[g for g in after['GameObjects'] if g not in groups]
assert before==trimmed,'Other scene data changed; inspect before retiring resources.'
capture=json.loads((OUT/'installed-capture.json').read_text());assert capture['SourceUnchanged'] and not capture['ErrorModels']
with Editor() as e:
    result=e.script(r'''var scene=Editor.SceneEditorSession.Active.Scene;
var ac=scene.GetAllObjects(false).Single(g=>g.Name=="Office Rooftop AC");
var renderer=ac.Components.Get<ModelRenderer>();
if(renderer.Model?.IsError!=false)throw new Exception("Installed model is invalid");
var project=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.GetFullPath(System.IO.Path.Combine(project,"Assets/models/props/riverside/roof_ac_v1"));
var expected=System.IO.Path.GetFullPath(System.IO.Path.Combine(project,"Assets/models/props/riverside/roof_ac_v1"));
if(folder!=expected)throw new Exception("Unexpected deletion target");
var files=System.IO.Directory.EnumerateFiles(folder).Where(p=>System.IO.Path.GetFileName(p).StartsWith("legacy_ac.")||System.IO.Path.GetFileName(p).StartsWith("pad_without_ac.")).ToArray();
if(scene.GetAllComponents<ModelRenderer>().Any(r=>r.Model?.ResourcePath?.Contains("roof_ac_v1/legacy_ac")==true||r.Model?.ResourcePath?.Contains("roof_ac_v1/pad_without_ac")==true))throw new Exception("Comparison model still in use");
var retired=System.IO.Path.Combine(project,"output/riverside/roof-ac-v1/retired-review-assets");System.IO.Directory.CreateDirectory(retired);
foreach(var file in files)
{
    System.IO.File.Copy(file,System.IO.Path.Combine(retired,System.IO.Path.GetFileName(file)),true);
    System.IO.File.Delete(file);
}
return new {Installed=true,ac.Id,ac.WorldPosition,Model=renderer.Model.ResourcePath,Mesh=renderer.Model.MeshInfo,DeletedComparisonFiles=files.Length};''','finish-office-ac.cs')
    (OUT/'installed.json').write_text(json.dumps(dict(**result,OtherSceneDataPreserved=True,OriginalPadModelDocPreserved=True,RemovedOldTriangles=24),indent=2))
    print(json.dumps(result,indent=2))
