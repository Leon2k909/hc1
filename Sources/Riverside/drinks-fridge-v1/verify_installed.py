"""Check the public model in play without runtime replacement geometry."""
from pathlib import Path
import json,hashlib,sys
from PIL import Image,ImageChops,ImageStat
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
if '--report-only' not in sys.argv:
 result=call('asset_compile',dict(path='models/maps/riverside/riverside_store.vmdl',full=False));print(json.dumps(result),flush=True);assert result['Success']
model=script(HERE/'check-installed.cs.txt');assert not model['IsError']
expected={f'materials/riverside/drinks-fridge-v1/{p}.vmat' for p in ('enamel','liner','frame','steel','red','blue','green','label','glass')}
assert expected<=set(model['Materials'])
source=(HERE/'runtime_review.cs.txt').read_text(encoding='utf-8').replace('runtime-review','runtime-installed')
start=source.index(' ModelRenderer architecture,');end=source.index(' var views=',start)
source=source[:start]+source[end:]
source=source.replace('new[]{"before","after"}','new[]{"installed"}')
source='\n'.join(l for l in source.splitlines() if not l.strip().startswith(('architecture.Model=','replacement.GameObject.Enabled=')))
(HERE/'runtime_installed.cs.txt').write_text(source,encoding='utf-8')
capture=(HERE/'capture.py').read_text(encoding='utf-8').replace("filename='runtime_review.cs.txt'","filename='runtime_installed.cs.txt'").replace("OUT/'play-state-restored.json'","OUT/'installed-play-state-restored.json'")
if '--report-only' not in sys.argv:exec(compile(capture,str(HERE/'capture.py'),'exec'))
checked=json.loads((OUT/'runtime-installed/checked.json').read_text())
assert checked['ActualPlayMode'] and checked['PlayerCount']>0 and not checked['ErrorModels']
restored=json.loads((OUT/'installed-play-state-restored.json').read_text());assert restored['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert restored['before'][field]==restored['after'][field]
baseline=json.loads((OUT/'install-baseline.json').read_text())
changed=[p for p,h in baseline['files'].items() if sha(ROOT/p)!=h]
assert set(changed)=={'Assets/models/maps/riverside/riverside_store.vmdl','Tools/riverside_map.py'},changed
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
old=(OUT/'install-before/riverside_store.vmdl').read_text();new=(ROOT/'Assets/models/maps/riverside/riverside_store.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):]
a=Image.open(OUT/'runtime-review/fridge-after.png').convert('RGB');b=Image.open(OUT/'runtime-installed/fridge-installed.png').convert('RGB')
assert a.size==b.size;diff=ImageChops.difference(a,b)
regions={'header':(280,145,590,190),'stock_and_shelves':(295,300,565,880),'compressor_grille':(290,974,580,1020)}
errors={name:sum(ImageStat.Stat(diff.crop(rect)).mean)/3 for name,rect in regions.items()}
assert max(errors.values())<12,errors
report=dict(installed=True,fridges=1,actual_play_mode_checked=True,loaded_private_materials=len(expected),physics_unchanged=True,
 scene_unchanged=True,other_assets_unchanged=True,generator_matches_approved=True,legacy_light_preserved=True,
 preexisting_changed_files=baseline['preexisting_changed_files'],changed_original_files=changed,
 approved_appearance_mean_pixel_error=errors,editor_state_restored=True,capture=checked,restoration=restored)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
