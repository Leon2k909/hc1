from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/main-airlock-sign-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());before=(OUT/'install-before/original-hall.obj').read_text().splitlines(keepends=True)
assert (ROOT/'Assets'/m['active_base']).read_text()==''.join(l for i,l in enumerate(before) if i not in set(m['cut']))
a=json.loads((OUT/'install-before/ares.scene').read_text());b=json.loads((ROOT/'Assets/scenes/maps/Ares/ares.scene').read_text());nodes=b['GameObjects'];new=[n for n in nodes if n.get('Name')=='Main Airlock Lightbox'];assert len(new)==1
b['GameObjects']=[n for n in nodes if n not in new];assert a==b
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Ares/ares.scene'):assert sha(ROOT/p)==h,p
sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A,map_kit as K,ares_main_airlock_sign as S
model=K.Model();A.lit_sign(model,'airlock07',(0,-1398.5,250),(0,1),128,32);assert model.triangle_count()==0
assert S.scene_object(K.SceneIds('7dffbb93-8cc1-4b8a-b28c-d66c4ef3c591'))==new[0]
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==460 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_14_faces_removed=True,only_one_renderer_added=True,unrelated_scene_and_materials_preserved=True,generator_retains_upgrade=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
