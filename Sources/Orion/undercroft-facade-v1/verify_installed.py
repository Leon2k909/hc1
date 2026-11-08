from pathlib import Path
import json,hashlib,sys,ast
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/orion/undercroft-facade-v1';sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();m=json.loads((OUT/'manifest.json').read_text())
old=(OUT/'install-before/original-launch-deck.obj').read_text().splitlines(keepends=True);new=(ROOT/'Assets/models/maps/orion/orion_launch_deck.obj').read_text();cut=set(m['cut']);assert len(cut)==50 and new==''.join(l for i,l in enumerate(old) if i not in cut)
a=json.loads((OUT/'install-before/orion.scene').read_text(encoding='utf-8'));b=json.loads((ROOT/'Assets/scenes/maps/Orion/orion.scene').read_text(encoding='utf-8'));nodes=[n for n in b['GameObjects'] if n.get('Name')=='Orion Undercroft Façade'];assert len(nodes)==1
b['GameObjects']=[n for n in b['GameObjects'] if n not in nodes];assert a==b
for p,h in m['protected'].items():
 if p not in ('Assets/models/maps/orion/orion_launch_deck.obj','Assets/scenes/maps/Orion/orion.scene'):assert sha(ROOT/p)==h,p
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K,orion_undercroft_facade as F
assert F.scene_object(K.SceneIds('cd0fd89c-6ca4-4cf3-aa26-145601afc2e5'))==nodes[0]
assert len(nodes[0]['Children'])==2 and all(c['Components'][0]['Radius']==90 and c['Components'][0]['Shadows'] for c in nodes[0]['Children'])
text=(ROOT/'Tools/orion_map.py').read_text();assert 'skip=("-n",)' in text and 'undercroft_facade_object(ids)' in text and 'dn0 - 0.1, dn0, 10, 96' not in text
r=json.loads((OUT/'installed/validation.json').read_text());assert r['Installed'] and r['Triangles']==9588 and r['AddedColliders']==0 and r['SceneUnchanged'] and r['PlayStateUnchanged']
report=dict(installed=True,only_original_48_panel_and_2_wall_faces_removed=True,all_other_obj_records_preserved=True,original_physics_hulls_materials_preserved=True,one_facade_renderer_and_two_interior_lights_added=True,generator_retains_upgrade=True,native=r)
(OUT/'installed-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
