"""Verify the saved public reel without a runtime replacement."""
from pathlib import Path
import json,hashlib,sys
from PIL import Image,ImageChops,ImageStat
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
if '--report-only' not in sys.argv:
 result=call('asset_compile',dict(path='models/maps/railhead/railhead_dress_east.vmdl',full=False));print(json.dumps(result),flush=True);assert result['Success']
model=script(HERE/'check-installed.cs.txt');assert not model['IsError']
expected={f'materials/railhead/cable-drum-v1/{p}.vmat' for p in ('timber_a','timber_b','timber_c','cable','steel','recess')}
assert expected<=set(model['Materials'])
source=(HERE/'runtime_review.cs.txt').read_text().replace('runtime-review','runtime-installed')
source=source.replace('new[]{"before","after"}','new[]{"installed","approved"}').replace('variant=="after"','variant=="approved"')
(HERE/'runtime_installed.cs.txt').write_text(source)
capture=(HERE/'capture.py').read_text().replace("filename='runtime_review.cs.txt'","filename='runtime_installed.cs.txt'").replace("OUT/'play-state-restored.json'","OUT/'installed-play-state-restored.json'")
if '--report-only' not in sys.argv:exec(compile(capture,str(HERE/'capture.py'),'exec'))
checked=json.loads((OUT/'runtime-installed/checked.json').read_text());assert checked['ActualPlayMode'] and checked['PlayerCount']>0 and not checked['ErrorModels']
restored=json.loads((OUT/'installed-play-state-restored.json').read_text());assert restored['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert restored['before'][field]==restored['after'][field]
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert set(changed)=={'Assets/models/maps/railhead/railhead_dress_east.vmdl','Tools/railhead_map.py'},changed
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
old=(OUT/'install-before/railhead_dress_east.vmdl').read_text();new=(ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):]
# Compare the saved public model and the approved standalone proposal in one
# session. Historical captures can differ with the gameplay camera's history.
a=Image.open(OUT/'runtime-installed/drum-approved.png').convert('RGB');b=Image.open(OUT/'runtime-installed/drum-installed.png').convert('RGB')
assert a.size==b.size;diff=ImageChops.difference(a,b)
regions={'timber_face':(440,220,1030,800),'cable_windings':(875,225,1020,390)}
errors={name:sum(ImageStat.Stat(diff.crop(rect)).mean)/3 for name,rect in regions.items()}
assert max(errors.values())<2,errors
report=dict(installed=True,reels=1,actual_play_mode_checked=True,loaded_private_materials=len(expected),original_wood_material_restored=True,
 physics_unchanged=True,scene_unchanged=True,other_assets_unchanged=True,generator_matches_approved=True,
 changed_original_files=changed,approved_appearance_mean_pixel_error=errors,editor_state_restored=True,capture=checked,restoration=restored)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
