"""Archive and remove only this task's unreferenced obsolete review base."""
from pathlib import Path
import hashlib,json
from native import ROOT,OUT,script
HERE=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((OUT/'installed.json').read_text())['columns']==4
folder=ROOT/'Assets/models/maps/railhead/ashtray-v1'
targets=[p for p in folder.iterdir() if p.name in {'east_without_ashtray.obj','east_without_ashtray.obj.meta','east_without_ashtray.mtl','east_without_ashtray.mtl.meta','east_without_ashtray.vmdl','east_without_ashtray.vmdl.meta','east_without_ashtray.vmdl_c'}]
assert targets
refs=[]
for p in (ROOT/'Assets').rglob('*'):
 if not p.is_file() or p in targets or p.suffix not in {'.vmdl','.scene','.prefab','.vmat','.json','.resource'}:continue
 if 'east_without_ashtray' in p.read_text(encoding='utf-8',errors='replace'):refs.append(str(p.relative_to(ROOT)))
assert not refs,refs
archive=OUT/'retired-preview';archive.mkdir(exist_ok=True)
items=[]
for p in targets:
 q=archive/p.name;q.write_bytes(p.read_bytes());assert sha(p)==sha(q)
 items.append(dict(path=str(p.relative_to(ROOT)).replace('\\','/'),sha256=sha(p),archive=str(q.relative_to(ROOT)).replace('\\','/')))
(OUT/'retire-plan.json').write_text(json.dumps(dict(files=items,external_references=refs),indent=2))
source='''var root=Sandbox.Project.Current.GetRootPath();
var folder=System.IO.Path.Combine(root,"output/railhead/ashtray-v1");
var plan=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder,"retire-plan.json")));
string Hash(string p)=>Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(p))).ToLowerInvariant();
foreach(var item in plan["files"].AsArray()) {
 var rel=item["path"].GetValue<string>();
 if(!rel.StartsWith("Assets/models/maps/railhead/ashtray-v1/east_without_ashtray.")||rel.Contains(".."))throw new InvalidOperationException("Unexpected deletion target");
 if(Hash(System.IO.Path.Combine(root,rel))!=item["sha256"].GetValue<string>()||Hash(System.IO.Path.Combine(root,item["archive"].GetValue<string>()))!=item["sha256"].GetValue<string>())throw new InvalidOperationException("Preview or archive changed");
}
var removed=new System.Collections.Generic.List<string>();
foreach(var item in plan["files"].AsArray()) {var rel=item["path"].GetValue<string>();System.IO.File.Delete(System.IO.Path.Combine(root,rel));removed.Add(rel);}
return new {Removed=removed,Archived=true};
'''
(HERE/'retire-preview.cs.txt').write_text(source)
result=script(HERE/'retire-preview.cs.txt');assert all(not p.exists() for p in targets)
(OUT/'obsolete-preview-cleanup.json').write_text(json.dumps(dict(result=result,files=items,external_references=refs),indent=2));print(json.dumps(result,indent=2))
