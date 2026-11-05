"""Check all four saved columns and exact removal of every live old render mesh."""
from pathlib import Path
import json,hashlib,sys,collections
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
if '--report-only' not in sys.argv and '--capture-only' not in sys.argv:
 for side in ('east','west'):
  r=call('asset_compile',dict(path=f'models/maps/railhead/railhead_dress_{side}.vmdl',full=False));print(json.dumps(r),flush=True);assert r['Success']
source=(HERE/'runtime_review.cs.txt').read_text().replace('runtime-review','runtime-installed')
a=source.index(' ModelRenderer architecture,');b=source.index(' var views=',a);source=source[:a]+source[b:]
a=source.index(' var views=');b=source.index(' foreach(var variant',a)
source=source[:a]+''' var views=new[]{
 new {Name="east-island",Eye=new Vector3(-936,-630,43),Target=new Vector3(-891,-601,20),Fov=34f,Width=900,Height=1200},
 new {Name="east-outer",Eye=new Vector3(-936,-1160,43),Target=new Vector3(-891,-1131,20),Fov=34f,Width=900,Height=1200},
 new {Name="west-island",Eye=new Vector3(-936,572,43),Target=new Vector3(-891,601,20),Fov=34f,Width=900,Height=1200},
 new {Name="west-outer",Eye=new Vector3(-936,1102,43),Target=new Vector3(-891,1131,20),Fov=34f,Width=900,Height=1200}};
'''+source[b:]
source=source.replace('new[]{"before","after"}','new[]{"installed"}')
source='\n'.join(l for l in source.splitlines() if not l.strip().startswith(('architecture.Model=','replacement.GameObject.Enabled=')))
(HERE/'runtime_installed.cs.txt').write_text(source)
capture=(HERE/'capture.py').read_text().replace("filename='runtime_review.cs.txt'","filename='runtime_installed.cs.txt'").replace("OUT/'play-state-restored.json'","OUT/'installed-play-state-restored.json'")
if '--report-only' not in sys.argv:exec(compile(capture,str(HERE/'capture.py'),'exec'))
checked=json.loads((OUT/'runtime-installed/checked.json').read_text());assert checked['ActualPlayMode'] and checked['PlayerCount']>0 and not checked['ErrorModels']
state=json.loads((OUT/'installed-play-state-restored.json').read_text());assert state['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert state['before'][field]==state['after'][field]
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert set(changed)==set(plan['before'])|{'Tools/railhead_dress_detail.py'},changed
for rel in plan['before']:
 old=(OUT/'install-before'/rel).read_text();new=(ROOT/rel).read_text()
 if rel.endswith('.vmdl'):
  marker='_class = "PhysicsShapeList"';assert old[old.index(marker):]==new[new.index(marker):]
 else:
  old=old.splitlines();new=new.splitlines();assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
  a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==588
for side in ('east','west'):
 obj=(ROOT/f'Assets/models/maps/railhead/ashtray-v1/installed_ashtrays_{side}.obj').read_text();assert sum(l.startswith('f ') for l in obj.splitlines())==19824
assert 'model.cylinder' not in (ROOT/'Tools/railhead_dress_detail.py').read_text().split('def ashtray_pillar(')[1].split('def wall_sign(')[0]
report=dict(installed=True,columns=4,old_render_triangles_removed=1176,new_triangles=39648,generator_matches_approved=True,legacy_generator_removed=True,physics_unchanged=True,scene_unchanged=True,unrelated_geometry_preserved=True,actual_play_mode_checked=True,native_error_models=[],editor_state_restored=True,capture=checked,restoration=state)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
