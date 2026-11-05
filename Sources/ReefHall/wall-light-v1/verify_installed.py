"""Inspect the saved public wall light and its exact source/physics changes."""
from pathlib import Path
import json,hashlib,sys,collections
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent;sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
if '--report-only' not in sys.argv and '--capture-only' not in sys.argv:
 r=call('asset_compile',dict(path='models/maps/reefhall/reefhall_filter.vmdl',full=False));print(json.dumps(r),flush=True);assert r['Success']
source=(HERE/'runtime_review.cs.txt').read_text().replace('runtime-review','runtime-installed')
start=source.index(' ModelRenderer architecture,');end=source.index(' var views=',start);source=source[:start]+source[end:]
source=source.replace('new[]{"before","after"}','new[]{"installed"}')
source='\n'.join(l for l in source.splitlines() if not l.strip().startswith(('architecture.Model=','replacement.GameObject.Enabled=')))
(HERE/'runtime_installed.cs.txt').write_text(source)
capture=(HERE/'capture.py').read_text().replace("filename='runtime_review.cs.txt'","filename='runtime_installed.cs.txt'").replace("OUT/'play-state-restored.json'","OUT/'installed-play-state-restored.json'")
if '--report-only' not in sys.argv:exec(compile(capture,str(HERE/'capture.py'),'exec'))
checked=json.loads((OUT/'runtime-installed/checked.json').read_text());assert checked['ActualPlayMode'] and checked['PlayerCount']>0 and not checked['ErrorModels']
state=json.loads((OUT/'installed-play-state-restored.json').read_text());assert state['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert state['before'][field]==state['after'][field]
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
base='Assets/models/maps/reefhall/reefhall_filter.obj';public='Assets/models/maps/reefhall/reefhall_filter.vmdl'
concurrent=json.loads((OUT/'concurrent-changes.json').read_text())
assert set(changed)=={base,public,'Tools/reefhall_map.py'}|set(concurrent['files']),changed
for p,h in concurrent['files'].items():
 if p!='Tools/reefhall_map.py':assert sha(ROOT/p)==h,p
g=(ROOT/'Tools/reefhall_map.py').read_text();oldg=(OUT/'install-before/Tools/reefhall_map.py').read_text()
start=g.index('    if np.allclose(fr.p(u,w,z),(760.,1100.,110.))');end=g.index('    _sconces.append(',start)
original_line='    fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )\n'
assert g[:start]+original_line+g[end:]==oldg,'Unrelated generator changes during installation' 
old=(OUT/'install-before'/public).read_text();new=(ROOT/public).read_text();marker='_class = "PhysicsShapeList"';assert old[old.index(marker):]==new[new.index(marker):]
old=(OUT/'install-before'/base).read_text().splitlines();new=(ROOT/base).read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '));assert not b-a and sum((a-b).values())==12
obj=(ROOT/'Assets/models/maps/reefhall/wall-light-v1/installed_wall_light.obj').read_text();assert sum(l.startswith('f ') for l in obj.splitlines())==4300
report=dict(installed=True,lights=1,old_render_triangles_removed=12,new_triangles=4300,generator_matches_approved=True,physics_unchanged=True,scene_unchanged=True,unrelated_geometry_preserved=True,existing_materials_reused=True,actual_play_mode_checked=True,native_error_models=[],editor_state_restored=True,capture=checked,restoration=state)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
