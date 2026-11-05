"""Validate the public installed model in play, without a runtime replacement."""
from pathlib import Path
import json,hashlib,sys
from PIL import Image,ImageChops,ImageStat
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
model=script(HERE/'check-installed.cs.txt')
assert not model['IsError']
expected={f'materials/railhead/road-barrier-v1/{p}.vmat' for p in ('white','red','yellow','rubber','steel')}
assert expected <= set(model['Materials'])
print(json.dumps(dict(installed_model_loaded=True,barrier_materials_loaded=len(expected))),flush=True)
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
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert set(changed)=={'Assets/models/maps/railhead/railhead_dress_east.vmdl','Tools/railhead_map.py'},changed
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
old=(OUT/'install-before/railhead_dress_east.vmdl').read_text();new=(ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):]
a=Image.open(OUT/'runtime-review/barrier-after.png').convert('RGB');b=Image.open(OUT/'runtime-installed/barrier-installed.png').convert('RGB')
assert a.size==b.size;diff=ImageChops.difference(a,b)
regions={'board':(480,145,1140,285),'left_foot':(445,690,650,770)}
errors={name:sum(ImageStat.Stat(diff.crop(rect)).mean)/3 for name,rect in regions.items()}
report=dict(installed=True,barriers=1,location='Railhead east yard (1905,-1556,0)',actual_play_mode_checked=True,
            loaded_private_materials=5,physics_unchanged=True,scene_unchanged=True,other_assets_unchanged=True,
            generator_matches_approved=True,changed_original_files=changed,approved_appearance_mean_pixel_error=errors,
            editor_state_restored=True,capture=checked,restoration=restored)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','restoration')},indent=2))
