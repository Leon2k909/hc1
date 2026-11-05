from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native
OUT=Path(tempfile.gettempdir())/'belltower-sack-pile-v2';native.OUT=OUT
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
m=json.loads((OUT/'install-stage/manifest.json').read_text())
assert all(sha(ROOT/p)==r['after'] for p,r in m['files'].items())
assert all(sha(ROOT/p)==h for p,h in m['protected'].items())
assert all(not (ROOT/p).exists() for p in m['deleted'])
assert all(json.loads((OUT/f'installed-compile-{Path(p).stem}.json').read_text())['Success'] for p in m['compile_models'])
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,belltower_map as B
namespace=dict(vars(B));exec((OUT/'install-stage/legacy-sacks.py.txt').read_text(),namespace)
old=K.Model();new=K.Model();namespace['sacks'](old,(-1215,730),0,7);B.sacks(new,(-1215,730),0,7)
assert str(old.boxes)==str(new.boxes) and str(old.hulls)==str(new.hulls)
assert len(new.props)==1 and new.triangle_count()==0
verify='''var session=Editor.SceneEditorSession.All.Single(s=>s.Scene.IsEditor && s.Scene.Source?.ResourcePath=="scenes/maps/belltower/belltower.scene");
var piles=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.StartsWith("models/maps/belltower/sack-pile-v2/sack_pile")==true).ToArray();
if(piles.Length!=2 || piles.Any(r=>r.Model.IsError) || session.HasUnsavedChanges)throw new InvalidOperationException("Saved piles differ.");
return new{SavedPiles=2,TotalSacks=14,ModelsLoaded=true,SceneSaved=true};'''
(HERE/'verify-installed.cs.txt').write_text(verify);print(native.script(HERE/'verify-installed.cs.txt','verify-installed'))
receipt=json.loads((OUT/'install-stage/installed.json').read_text());receipt.update(json.loads((OUT/'install-stage/deleted.json').read_text()));receipt['RegeneratedCollisionIdentical']=True
(HERE/'installed.json').write_text(json.dumps(receipt,indent=2))
s=(ROOT/'Sources/Belltower/wall-lantern-v2/capture_installed.py').read_text().replace('wall-lantern-v2','sack-pile-v2').replace('position=(443,1915,127);target=(475,1858,116)','position=(805,1130,68);target=(730,1215,20)').replace("'fov':38","'fov':48")
(HERE/'capture_installed.py').write_text(s)
# Future accepted builds stage only the current resources, with both handednesses.
p=HERE/'build.py';s=p.read_text();a=s.index('def main():');s=s[:a]+'''def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    L.RES=RES;L.MAPS=MAPS
    for i in range(3):
        model=build(i)
        K.write_obj(MODEL/f'lantern_lod{i}.obj',model,f'lantern_lod{i}')
        K.write_obj(MODEL/f'mirrored_lod{i}.obj',model.mirrored(),f'mirrored_lod{i}')
    doc=L.modeldoc()
    (MODEL/'sack_pile.vmdl').write_text(doc)
    (MODEL/'sack_pile_mirrored.vmdl').write_text(doc.replace('lantern_lod','mirrored_lod'))
    print('Accepted sack piles staged; retired review resources not recreated.')
if __name__=='__main__':main()
''';p.write_text(s)
print(receipt)
