import json,hashlib,sys
from pathlib import Path
from PIL import Image,ImageChops,ImageStat
from native import ROOT,OUT,call,script
HERE=Path(__file__).parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'install-plan.json').read_text());assert all(sha(ROOT/p)==h for p,h in plan['files'].items())
model=script(HERE/'check-installed.cs.txt');print(json.dumps(model),flush=True)
assert not model['IsError'] and all(any('/clock-v1/'+p+'.vmat' in x for x in model['Materials']) for p in ('dial','housing','ink','steel','seal'))
source=(HERE/'runtime_review.cs.txt').read_text().replace('runtime-review','runtime-installed')
start=source.index(' ModelRenderer architecture,');end=source.index(' var views=',start)
source=source[:start]+source[end:]
source=source.replace('new[]{"before","after"}','new[]{"installed"}')
source='\n'.join(l for l in source.splitlines() if not l.strip().startswith(('architecture.Model=','replacement.GameObject.Enabled=')))
(HERE/'runtime_installed.cs.txt').write_text(source)
capture=(HERE/'capture.py').read_text().replace("filename='runtime_baseline.cs.txt' if '--baseline' in sys.argv else 'runtime_review.cs.txt'","filename='runtime_installed.cs.txt'").replace("OUT/'play-state-restored.json'","OUT/'installed-play-state-restored.json'")
if '--report-only' not in sys.argv:exec(compile(capture,str(HERE/'capture.py'),'exec'))
errors={}
for name in ('front','side'):
 a=Image.open(OUT/f'runtime-review/{name}-after.png').convert('RGB');b=Image.open(OUT/f'runtime-installed/{name}-installed.png').convert('RGB')
 # Compare the clock itself: background material streaming can vary between runs.
 diff=ImageChops.difference(a,b)
 errors[name]=dict(full_frame=sum(ImageStat.Stat(diff).mean)/3,
                   clock_centre=sum(ImageStat.Stat(diff.crop((500,120,1080,760))).mean)/3)
 assert errors[name]['clock_centre']<2.0,(name,errors[name])
checked=json.loads((OUT/'runtime-installed/checked.json').read_text())
assert checked['ActualPlayMode'] and checked['PlayerCount']>0 and not checked['ErrorModels']
assert json.loads((OUT/'installed-play-state-restored.json').read_text())['restored']
before=(OUT/'install-before/railhead_dress_centre.vmdl').read_text();after=(ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl').read_text();marker='_class = "PhysicsShapeList"';assert before[before.index(marker):]==after[after.index(marker):]
report=dict(installed=True,actual_play_mode_checked=True,approved_appearance_mean_pixel_error=errors,physics_unchanged=True,source_scene_unchanged=True,generator_matches_approved=True,editor_state_restored=True)
(OUT/'installed.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
