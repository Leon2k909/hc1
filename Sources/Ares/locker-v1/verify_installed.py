"""Check both installed banks without substituting runtime geometry."""
from pathlib import Path
import json,hashlib,sys,collections
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
if '--report-only' not in sys.argv:
 r=call('asset_compile',dict(path='models/maps/ares/ares_hall.vmdl',full=False));print(json.dumps(r),flush=True);assert r['Success']
loaded=script(HERE/'check-installed.cs.txt');assert not loaded['IsError']
assert {f'materials/ares/{p}.vmat' for p in ('ar_steel','ar_gunmetal','ar_dark','ar_brass','ar_white')}<=set(loaded['Materials'])
source=(HERE/'runtime_review.cs.txt').read_text().replace('runtime-review','runtime-installed').replace('new Vector2(900,1200)','new Vector2(1400,900)').replace('new Bitmap(900,1200)','new Bitmap(1400,900)')
start=source.index(' ModelRenderer architecture,');end=source.index(' var views=',start);source=source[:start]+source[end:]
start=source.index(' var views=');end=source.index(' foreach(var variant',start)
source=source[:start]+''' var views=new[]{
 new {Name="east-bank",Eye=new Vector3(-370,-1278,70),Target=new Vector3(-709,-1278,42),Fov=38f},
 new {Name="west-bank",Eye=new Vector3(-370,1278,70),Target=new Vector3(-709,1278,42),Fov=38f}};
'''+source[end:]
source=source.replace('new[]{"before","after"}','new[]{"installed"}')
source='\n'.join(l for l in source.splitlines() if not l.strip().startswith(('architecture.Model=','replacement.GameObject.Enabled=')))
(HERE/'runtime_installed.cs.txt').write_text(source)
capture=(HERE/'capture.py').read_text().replace("filename='runtime_review.cs.txt'","filename='runtime_installed.cs.txt'").replace("OUT/'play-state-restored.json'","OUT/'installed-play-state-restored.json'")
if '--report-only' not in sys.argv:exec(compile(capture,str(HERE/'capture.py'),'exec'))
checked=json.loads((OUT/'runtime-installed/checked.json').read_text());assert checked['ActualPlayMode'] and checked['PlayerCount']>0 and not checked['ErrorModels']
state=json.loads((OUT/'installed-play-state-restored.json').read_text());assert state['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert state['before'][field]==state['after'][field]
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert set(changed)=={'Assets/models/maps/ares/ares_hall.vmdl','Assets/models/maps/ares/pressure-doors-v2/hall_base.obj','Tools/ares_map.py'},changed
rel='Assets/models/maps/ares/ares_hall.vmdl';old=(OUT/'install-before'/rel).read_text();new=(ROOT/rel).read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):]
rel='Assets/models/maps/ares/pressure-doors-v2/hall_base.obj';old=(OUT/'install-before'/rel).read_text().splitlines();new=(ROOT/rel).read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==336
obj=(ROOT/'Assets/models/maps/ares/locker-v1/installed_lockers.obj').read_text();assert sum(l.startswith('f ') for l in obj.splitlines())==plan['new_triangles']==75074
assert sorted(p['number'] for p in plan['positions'])==list(range(1,15))
report=dict(installed=True,lockers=14,old_render_triangles_removed=336,new_total_triangles=75074,unique_numbers=list(range(1,15)),generator_matches_approved=True,physics_unchanged=True,scene_unchanged=True,unrelated_geometry_preserved=True,existing_materials_reused=True,actual_play_mode_checked=True,native_error_models=[],editor_state_restored=True,capture=checked,restoration=state)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
