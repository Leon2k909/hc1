from pathlib import Path
import collections,hashlib,json
from PIL import Image,ImageDraw,ImageFont
from native import ROOT,OUT,call
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=json.loads((OUT/'source-guard.json').read_text())
assert all(sha(ROOT/p)==h for p,h in guard.items()),'An installed source changed during review'
manifest=json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
old=(ROOT/manifest['source']).read_text().splitlines()
new=(ROOT/'Assets/models/maps/lowtide/quay-ladder-v1/east_without_ladder.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '))
assert not b-a and sum((a-b).values())==168
orig=(ROOT/'Assets/models/maps/lowtide/lowtide_east.vmdl').read_text()
preview=(ROOT/'Assets/models/maps/lowtide/quay-ladder-v1/east_without_ladder.vmdl').read_text()
assert orig[orig.index('_class = "PhysicsShapeList"'):]==preview[preview.index('_class = "PhysicsShapeList"'):]
capture=json.loads((OUT/'capture-before-after.json').read_text())
assert capture['UserStatePreserved'] and not capture['ErrorModels']
status=call('editor_status');assert status['LastCompileSucceeded'] and not status['LastCompileErrors']
font=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),36)
small=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),24)
for name in ('ladder','landing','detail'):
    source='landing' if name=='detail' else name
    imgs=[Image.open(OUT/f'{source}-{v}.png').convert('RGB') for v in ('before','after')]
    if name=='detail':imgs=[im.crop((600,110,1060,880)) for im in imgs]
    w,h=imgs[0].size;sheet=Image.new('RGB',(2*w+24,h+116),(18,23,26));d=ImageDraw.Draw(sheet)
    for i,(im,label) in enumerate(zip(imgs,('BEFORE','AFTER'))):
        x=i*(w+24);sheet.paste(im,(x,60));d.text((x+24,10),label,font=font,fill=(232,237,234))
    caption='LOWTIDE / QUAY LADDER · MATCHED NATIVE CAPTURES' if name=='detail' else 'LOWTIDE / QUAY LADDER     Native engine captures · identical camera, lighting and exposure'
    d.text((24,h+78),caption,font=small,fill=(174,191,187))
    sheet.save(OUT/f'{name}-comparison.png')
report=dict(review_only=True,replacement_triangles=manifest['triangles'],original_triangles_replaced=168,original_files_checked=len(guard),original_assets_unchanged=True,unrelated_geometry_unchanged=True,physics_unchanged=True,native_error_models=[],user_state_preserved=True,streaming_frames_per_view=90,forced_texture_residency=False,editor_status=status)
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='editor_status'},indent=2))
