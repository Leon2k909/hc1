from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/railhead/city-light-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((OUT/'manifest.json').read_text())
changed={'Assets/scenes/maps/Railhead/railhead.scene'}
for part in m['parts']:
 old=(OUT/'install-before'/(part['part']+'.obj')).read_text().splitlines(keepends=True);new=(ROOT/'Assets'/part['active_base']).read_text();cut=set(part['cut'])
 assert new==''.join(l for i,l in enumerate(old) if i not in cut) and len(cut)==part['original_faces']
 changed.add('Assets/'+part['active_base'])
scene=json.loads((ROOT/'Assets/scenes/maps/Railhead/railhead.scene').read_text());before=json.loads((OUT/'install-before/railhead.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='East Concourse Poster Lightbox'];assert len(nodes)==1
scene['GameObjects']=[n for n in scene['GameObjects'] if n not in nodes];assert scene==before
for p,h in m['protected'].items():
 if p not in changed:assert sha(ROOT/p)==h,p
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,railhead_dress_detail as D,railhead_city_light as L
model=K.Model();position=D.city_light(model,545.,1299.5,'-n','poster_sea',bottom=34.);legacy=K.Model();oldposition=D.legacy_city_light(legacy,545.,1299.5,'-n','poster_sea',bottom=34.)
assert model.triangle_count()==0 and not model.boxes and not model.hulls and position==oldposition
assert L.scene_object(K.SceneIds('1c380621-cecc-456b-89b4-c92b52a0e13d'))==nodes[0]
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==1964 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_94_opaque_and_2_glass_faces_removed=True,all_other_obj_records_preserved=True,only_one_renderer_added=True,unrelated_scene_models_physics_materials_preserved=True,generator_retains_upgrade_and_original_light_return=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
