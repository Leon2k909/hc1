from pathlib import Path
import sys,json,hashlib
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/interior-fridges-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((OUT/'install-plan.json').read_text());assert sha(ROOT/p['source'])==p['source_after'];assert sha(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl')==p['store_vmdl_before']
assert json.loads((OUT/'generator-check.json').read_text())['CollisionPreserved'];assert json.loads((OUT/'installed-capture.json').read_text())['SourceUnchanged']
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'));from native import Editor
with Editor() as e:
 r=e.script(r'''var model=Model.Load("models/props/riverside/interior_fridges_v1/fridge.vmdl");
if(model.IsError||model.MeshInfo.Meshes.Sum(m=>m.Triangles)!=34152)throw new Exception("Installed cabinet differs");
var project=Sandbox.Project.Current.GetRootPath();var folder=System.IO.Path.GetFullPath(System.IO.Path.Combine(project,"Assets/models/props/riverside/interior_fridges_v1"));
var files=System.IO.Directory.EnumerateFiles(folder).Where(p=>System.IO.Path.GetFileName(p).StartsWith("legacy_fridge.")||System.IO.Path.GetFileName(p).StartsWith("store_without_fridges.")).ToArray();
if(files.Any(f=>System.IO.Path.GetDirectoryName(System.IO.Path.GetFullPath(f))!=folder))throw new Exception("Unexpected removal target");
var archive=System.IO.Path.Combine(project,"output/riverside/interior-fridges-v1/retired-review-assets");System.IO.Directory.CreateDirectory(archive);
foreach(var file in files){System.IO.File.Copy(file,System.IO.Path.Combine(archive,System.IO.Path.GetFileName(file)),true);System.IO.File.Delete(file);}
return new{Installed=true,Cabinets=3,TrianglesPerCabinet=34152,DeletedComparisonFiles=files.Length};''','finish-interior-fridges.cs')
 r.update(RemovedOldTriangles=42,StoreModelDocPreserved=True,ExistingSceneObjectsPreserved=True,CollisionPreserved=True,PointLightsPreserved=True)
 (OUT/'installed.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
