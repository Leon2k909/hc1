from pathlib import Path
import json,hashlib,collections
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from native import ROOT,OUT,call
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert not changed,changed
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
old=(ROOT/manifest['source']).read_text().splitlines();new=(ROOT/'Assets/models/maps/reefhall/pump-v1/filter_without_pump.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '))
assert not b-a and sum((a-b).values())==manifest['original_triangles']==220
original=(ROOT/'Assets/models/maps/reefhall/reefhall_filter.vmdl').read_text();preview=(ROOT/'Assets/models/maps/reefhall/pump-v1/filter_without_pump.vmdl').read_text()
assert original[original.index('_class = "PhysicsShapeList"'):]==preview[preview.index('_class = "PhysicsShapeList"'):]
folder=OUT/'runtime-review';capture=json.loads((folder/'checked.json').read_text())
camera=json.loads((folder/'camera.json').read_text());assert 'PhotographicResponse' in camera['Effects'] and 'Tonemapping' in camera['Effects']
assert capture['ActualPlayMode'] and capture['ActiveRuntimeMap']=='scenes/maps/reefhall/reefhall.scene' and capture['PlayerCount']>0 and not capture['ErrorModels']
restored=json.loads((folder/'restored.json').read_text());assert restored['MenuRestored'] and restored['IsPlaying']
status=call('editor_status');assert status['ActiveScenePath']=='scenes/menu.scene' and status['IsPlaying'] and not status['SceneHasUnsavedChanges'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
font=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),38);small=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),24)
for name in ('pump','inlet','detail'):
    source='pump' if name=='detail' else name
    imgs=[Image.open(folder/f'{source}-{v}.png').convert('RGB') for v in ('before','after')]
    if name=='detail':imgs=[im.crop((390,80,1210,900)) for im in imgs]
    w,h=imgs[0].size;sheet=Image.new('RGB',(w*2+24,h+116),(18,23,26));d=ImageDraw.Draw(sheet)
    for i,(im,title) in enumerate(zip(imgs,('BEFORE','AFTER'))):
        x=i*(w+24);sheet.paste(im,(x,60));d.text((x+24,8),title,font=font,fill=(230,237,235))
    caption='REEF HALL / CIRCULATION PUMP · PLAY MODE' if name=='detail' else 'REEF HALL / CIRCULATION PUMP     Actual play mode · matching camera, lighting and exposure'
    d.text((24,h+78),caption,font=small,fill=(171,190,187))
    sheet.save(OUT/f'{name}-comparison.png')
report=dict(review_only=True,new_triangles=manifest['triangles'],replaced_triangles=220,guarded_original_files=len(guard),original_assets_unchanged=True,unrelated_geometry_unchanged=True,physics_unchanged=True,actual_play_mode_checked=True,player_present=True,native_error_models=[],menu_restored=True,forced_texture_residency=False,camera=camera,capture=capture,editor_status=status)
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','editor_status')},indent=2))
