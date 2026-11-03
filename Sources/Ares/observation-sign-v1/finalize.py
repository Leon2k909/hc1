from pathlib import Path
import json,hashlib,re,collections
from PIL import Image,ImageDraw,ImageFont
from native import ROOT,OUT,call
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=json.loads((OUT/'source-guard.json').read_text())
changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
assert not changed,changed
manifest=json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
source=ROOT/manifest['source'];before=source.read_text().splitlines()
after=(ROOT/'Assets/models/maps/ares/observation-sign-v1/dressing_without_sign.obj').read_text().splitlines()
assert [s for s in before if s.startswith(('v ','vt ','vn '))]==[s for s in after if s.startswith(('v ','vt ','vn '))]
oldfaces=collections.Counter(s for s in before if s.startswith('f '))
newfaces=collections.Counter(s for s in after if s.startswith('f '))
assert not newfaces-oldfaces
assert sum((oldfaces-newfaces).values())==30
oldv=(ROOT/'Assets/models/maps/ares/ares_dressing.vmdl').read_text()
newv=(ROOT/'Assets/models/maps/ares/observation-sign-v1/dressing_without_sign.vmdl').read_text()
assert oldv[oldv.index('_class = "PhysicsShapeList"'):]==newv[newv.index('_class = "PhysicsShapeList"'):]
capture=json.loads((OUT/'capture-before-after.json').read_text())
assert not capture['ErrorModels'] and capture['UserStatePreserved']
status=call('editor_status');compilers=call('compile_status')
assert status['Paths']['ProjectRoot'].lower()==str(ROOT).lower()
assert status['ActiveScene']=='ares' and not status['SceneHasUnsavedChanges'] and not status['IsPlaying']
assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
errors=[c for c in compilers['Compilers'] if c['Errors'] or c['Success'] is False]
assert not errors,errors
report=dict(review_only=True,guarded_original_files=len(guard),original_files_unchanged=True,unrelated_vertices_uvs_normals_unchanged=True,removed_triangles=30,replacement_triangles=manifest['triangles'],physics_suffix_unchanged=True,native_error_models=[],editor_state_preserved=True,editor_status=status,compile_status=compilers)
(OUT/'validation.json').write_text(json.dumps(report,indent=2))
font=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),32)
small=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),22)
for name,crop in [('detail',(330,280,1320,660)),('context',None)]:
    images=[Image.open(OUT/f'{name}-{variant}.png').convert('RGB') for variant in ('before','after')]
    if crop:images=[im.crop(crop) for im in images]
    w,h=images[0].size
    sheet=Image.new('RGB',(w*2+24,h+110),(18,23,26));d=ImageDraw.Draw(sheet)
    for idx,(im,title) in enumerate(zip(images,('BEFORE','AFTER'))):
        x=idx*(w+24);sheet.paste(im,(x,58));d.text((x+22,10),title,font=font,fill=(225,232,232))
    d.text((22,h+70),'ARES / OBSERVATION DECK     Native engine captures · identical camera, lighting and exposure',font=small,fill=(168,183,184))
    sheet.save(OUT/f'{name}-comparison.png')
print(json.dumps({k:v for k,v in report.items() if k not in ('editor_status','compile_status')},indent=2))
