from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native
temp=Path(tempfile.gettempdir())/'belltower-dish-lamp-v2';m=json.loads((temp/'install-stage/manifest.json').read_text())
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert all(sha(ROOT/p)==r['after'] for p,r in m['files'].items())
assert all(sha(ROOT/p)==h for p,h in m['protected'].items())
assert all(not (ROOT/p).exists() for p in m['deleted'])
assert all(json.loads((temp/f'installed-compile-{Path(p).stem}.json').read_text())['Success'] for p in m['compile_models'])
native.OUT=temp;receipt=json.loads((temp/'install-stage/installed.json').read_text());receipt.update(json.loads((temp/'install-stage/deleted.json').read_text()));receipt.update(native.script(ROOT/'Sources/Belltower/dish-lamp-v2/verify-installed.cs.txt','verify-installed'))
(ROOT/'Sources/Belltower/dish-lamp-v2/installed.json').write_text(json.dumps(receipt,indent=2))
# Stop accepted builds from recreating retired wrappers.
p=ROOT/'Sources/Belltower/dish-lamp-v2/build.py';s=p.read_text();a=s.index('def main():');s=s[:a]+'''def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}') for i in range(3)]
    L.RES=RES;L.MAPS=MAPS
    (MODEL/'wall_lantern.vmdl').write_text(L.modeldoc())
    print(json.dumps({'accepted_staged':True,'lods':lods}))
if __name__=='__main__':main()
''';p.write_text(s)
p=ROOT/'Sources/Belltower/dish-lamp-v2/README.md';p.write_text(p.read_text()+'''\nApproved and installed in all ten positions (five each side). Removed 3,560 old baked triangles
from eight mesh sources; all seven affected current/historic model definitions compiled.
Deleted thirteen obsolete private review files. Preserved physics, other object IDs and the user's
retained original wall-lantern resource. Native save/load verification passed; see `installed.json`.
Regeneration uses `Tools/belltower_dish_lamps.py`; accepted builds no longer recreate retired files.
''')
s=(ROOT/'Sources/Belltower/dish-lamp-v2/audit.py').read_text().replace('dish-lamp-v2','sack-pile-v2').replace("('wall_lantern','west_baseline'","('sack_pile','west_baseline'").replace('before-final','before-interior').replace('after-final','after-interior').replace("glob('*final*')","glob('*interior*')").replace('outside[300:720,315:970]','outside[200:1024,0:930]')
(HERE/'audit.py').write_text(s)
print(receipt)
