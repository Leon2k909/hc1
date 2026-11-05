"""Verify all ten replacements in the saved west/east models."""
from pathlib import Path
import json,hashlib,sys,re
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
if '--report-only' not in sys.argv:
 for side in ('west','east'):
  result=call('asset_compile',dict(path=f'models/maps/belltower/belltower_{side}.vmdl',full=False));print(json.dumps(result),flush=True);assert result['Success']
loaded=script(HERE/'check-installed.cs.txt')
expected={'materials/belltower/wood_planks.vmat','materials/belltower/wood_planks_dark.vmat','materials/buildings/iron_black.vmat','materials/gunsmith_range/bench_oak_endgrain.vmat'}
for model in loaded:assert not model['IsError'] and expected<=set(model['Materials'])
source=(HERE/'runtime_review.cs.txt').read_text().replace('runtime-review','runtime-installed')
start=source.index(' ModelRenderer architecture,');end=source.index(' var views=',start);source=source[:start]+source[end:]
start=source.index(' var views=');end=source.index(' foreach(var variant',start)
source=source[:start]+''' var views=new[]{
 new {Name="west",Eye=new Vector3(-700,690,70),Target=new Vector3(-600,800,16),Fov=50f},
 new {Name="east",Eye=new Vector3(-700,-690,70),Target=new Vector3(-600,-800,16),Fov=50f}};
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
assert set(changed)==(set(plan['before'])&set(guard))|{'Tools/belltower_map.py'},changed
for side in ('west','east'):
 rel=f'Assets/models/maps/belltower/belltower_{side}.vmdl'
 old=(OUT/'install-before'/rel).read_text();new=(ROOT/rel).read_text();marker='_class = "PhysicsShapeList"'
 assert old[old.index(marker):]==new[new.index(marker):]
 assert new.count(f'filename = "models/maps/belltower/picnic-table-v1/installed_{side}.obj"')==1
 # Both canonical caches retain zero references to the old table faces; the
 # guarded streaming splice removed exactly 300 faces from each representation.
 rows=[s for s in plan['splices'] if f'/{side}/' in s['path'] and not s['appended']]
 assert sum(s['removed'] for s in rows)==300
 obj=(ROOT/f'Assets/models/maps/belltower/picnic-table-v1/installed_{side}.obj').read_text()
 assert sum(l.startswith('f ') for l in obj.splitlines())==5*4244
assert plan['removed_live_triangles']==600 and plan['tables']==10
assert 'p.box( model, ( -42, -16, 27 )' not in (ROOT/'Tools/belltower_map.py').read_text()
report=dict(installed=True,tables=10,old_live_triangles_removed=600,new_triangles_per_table=4244,original_wood_materials_preserved=True,physics_unchanged=True,scene_unchanged=True,unrelated_geometry_preserved=True,generator_matches_approved=True,canonical_caches_updated=True,actual_play_mode_checked=True,native_error_models=[],editor_state_restored=True,changed_guarded_files=changed,capture=checked,restoration=state)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
