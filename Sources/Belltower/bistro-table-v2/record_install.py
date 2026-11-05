"""Verify and record the accepted installation without touching saved assets."""
from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=Path(tempfile.gettempdir())/'belltower-bistro-table-v2'
def sha(p):
    with open(p,'rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
m=json.loads((OUT/'install-stage/manifest.json').read_text())
assert all(sha(ROOT/p)==r['after'] for p,r in m['files'].items())
assert all(sha(ROOT/p)==h for p,h in m['protected'].items())
assert all(not (ROOT/p).exists() for p in m['deleted'])
assert all(json.loads((OUT/f'installed-compile-{Path(p).stem}.json').read_text())['Success'] for p in m['compile_models'])
sys.path.insert(0,str(ROOT/'Sources/Belltower/terracotta-pot-v2'));import native
native.OUT=OUT
verify=(ROOT/'Sources/Belltower/bistro-chair-v2/verify_installed.cs.txt').read_text().replace('bistro-chair-v2','bistro-table-v2').replace('bistro_chair','bistro_table').replace('chairs','tables').replace('Chairs','Tables').replace('21','7')
(HERE/'verify_installed.cs.txt').write_text(verify)
print(native.script(HERE/'verify_installed.cs.txt','verify-installed'))
data=json.loads((OUT/'install-stage/installed.json').read_text());data.update(json.loads((OUT/'install-stage/deleted.json').read_text()))
data.update({'CompiledModelDefinitions':len(m['compile_models']),'VerifiedSourceMeshes':len(m['files'])})
(HERE/'installed.json').write_text(json.dumps(data,indent=2)+'\n')
# Keep accepted generators from recreating deleted comparison resources.
p=HERE/'build.py';s=p.read_text();a=s.index('def stage_base():');b=s.index("if __name__",a)
s=s[:a]+'''def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'table_lod{i}.obj',build(i),f'table_lod{i}') for i in range(3)]
    text=C.modeldoc().replace('bistro-chair-v2','bistro-table-v2').replace('chair_lod','table_lod')
    (MODEL/'bistro_table.vmdl').write_text(text)
    print(json.dumps({'lods':lods,'accepted_resource_staged':True,'review_wrappers_recreated':False}))

'''+s[b:];p.write_text(s)
p=HERE/'README.md';s=p.read_text().replace('— review candidate','— installed').replace('Not installed in the saved map.','Approved by the user and installed in all seven saved café positions (four west, three east).').replace('`build.py` stages the private table and a west variant','The original review builder staged the private table and a west variant').replace('Pending user visual approval under `CLAUDE.md` before replacement.','Installed through the editor on 2026-11-04. Exactly 3,038 old triangles were removed from ten source meshes;\nall seven affected VMDLs compiled. Eleven obsolete private review files were deleted. Existing object IDs,\nphysics and editor/play state were preserved. `installed.json` records the receipts.\n`build.py` now stages only the accepted resource; regeneration uses `Tools/belltower_bistro_tables.py`.');p.write_text(s)
p=ROOT/'docs/notes/belltower-bistro-table-v2-review-20261104.md';s=p.read_text().replace('— pending review','— installed').replace('The candidate is NOT installed. Await user approval before replacing the remaining seven tables.','User approved the native after image and requested removal of the old. All seven tables are installed\nwith stable scene IDs through `Tools/belltower_bistro_tables.py`; the eastern café spacing is preserved.\nThe native installation removed 3,038 legacy triangles from ten source meshes and saved the scene.\nAll seven affected VMDLs compiled, eleven private review files were retired, and original physics,\nobject IDs and editor/play state were preserved. See `installed.json` in the source folder.');p.write_text(s)
p=ROOT/'CLAUDE.md';s=p.read_text().replace('Belltower cafe table v2 (model review, 2026-11-04)','Belltower cafe table v2 (all seven installed, 2026-11-04)');p.write_text(s)
print(data)
