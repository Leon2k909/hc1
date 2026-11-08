from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/riverside/storefront-depth-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((OUT/'manifest.json').read_text())
old=(OUT/'install-before/original-store.obj').read_text().splitlines(keepends=True);new=(ROOT/'Assets'/m['active_base']).read_text();cut=set(m['cut']);assert len(cut)==20 and new==''.join(l for i,l in enumerate(old) if i not in cut)
for p,h in m['protected'].items():
 if p not in ('Assets/'+m['active_base'],'Assets/scenes/maps/Riverside/riverside.scene'):assert sha(ROOT/p)==h,p
before=json.loads((OUT/'install-stage/live-before.json').read_text(encoding='utf-8'));after=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text(encoding='utf-8'));nodes=[n for n in after['GameObjects'] if n.get('Name')=='Lucky Stop Glazed Windows'];assert len(nodes)==1
after['GameObjects']=[n for n in after['GameObjects'] if n not in nodes]
def normalize(n):
 if isinstance(n,dict):
  n.pop('__PrefabIdToInstanceId',None)
  for v in n.values():normalize(v)
 elif isinstance(n,list):
  for v in n:normalize(v)
normalize(before);normalize(after);assert before['GameObjects']==after['GameObjects'],'Unrelated live objects differ in saved scene'
sys.path.insert(0,str(ROOT/'Tools'));import riverside_storefront_depth as F
node=F.scene_object();actual=nodes[0];assert actual['__guid']==node['__guid']
component=actual['Components'][0];path=component['Model'];path=path['Path'] if isinstance(path,dict) else path;assert path=='models/props/riverside/storefront_depth_v1/windows.vmdl' and component['__guid']==node['Components'][0]['__guid']
text=(ROOT/'Tools/riverside_map.py').read_text();assert 'objects.append(glazed_storefront_object())' in text and text.count('skip=("-n","+n")')==2 and 'P.lit( m, "window", wc' not in text
receipt=json.loads((OUT/'installed.json').read_text());assert receipt['Installed'] and receipt['UnrelatedLiveSceneUnchanged'] and receipt['NativeSceneSaved'] and receipt['PlayStateUnchanged']
native=json.loads((OUT/'installed/validation.json').read_text());assert native['Installed'] and native['ModelsValid'] and native['Lods']==3 and native['Triangles']==11648 and native['AddedColliders']==0 and native['SceneUnchanged'] and native['PlayStateUnchanged']
report=dict(installed=True,only_original_20_faces_removed=True,all_other_obj_records_preserved=True,public_modeldoc_imports_physics_shared_materials_preserved=True,unrelated_live_scene_objects_preserved=True,native_editor_serialization_used=True,one_renderer_added_no_lights_or_colliders=True,generator_retains_approved_windows_and_original_collision=True,native=native)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
