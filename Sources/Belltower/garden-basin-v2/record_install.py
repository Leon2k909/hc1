from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=Path(tempfile.gettempdir())/'belltower-gate-pier-v2';m=json.loads((OUT/'install-stage/manifest.json').read_text())
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert all(sha(ROOT/p)==r['after'] for p,r in m['files'].items());assert all(sha(ROOT/p)==h for p,h in m['protected'].items());assert all(not (ROOT/p).exists() for p in m['deleted'])
assert all(json.loads((OUT/f'installed-compile-{Path(p).stem}.json').read_text())['Success'] for p in m['compile_models'])
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,belltower_map as B
for e in (-459,-361):
    for n in (-405,-895):
        old=K.Model();new=K.Model();B._legacy_pier(old,(e,n),0,64);B.pier(new,(e,n),0,64)
        assert str(old.boxes)==str(new.boxes) and str(old.hulls)==str(new.hulls) and new.triangle_count()==0 and len(new.props)==1
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native;native.OUT=OUT
verify='''var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor && s.Scene.Source?.ResourcePath=="scenes/maps/belltower/belltower.scene");
var models=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath=="models/maps/belltower/gate-pier-v2/gate_pier.vmdl").ToArray();
if(models.Length!=8 || models.Any(r=>r.Model.IsError)||session.HasUnsavedChanges)throw new InvalidOperationException("Saved piers differ.");return new{SavedPiers=8,Loaded=true,SceneSaved=true};'''
p=ROOT/'Sources/Belltower/gate-pier-v2/verify-installed.cs.txt';p.write_text(verify);print(native.script(p,'verify-installed'))
r=json.loads((OUT/'install-stage/installed.json').read_text());r.update(json.loads((OUT/'install-stage/deleted.json').read_text()));r['RegeneratedCollisionIdentical']=True;(ROOT/'Sources/Belltower/gate-pier-v2/installed.json').write_text(json.dumps(r,indent=2))
p=ROOT/'Sources/Belltower/gate-pier-v2/build.py';s=p.read_text();a=s.index('old=K.Model()');p.write_text(s[:a]+"print({'accepted_resource_staged':True,'lods':lods})\n")
print(r)
