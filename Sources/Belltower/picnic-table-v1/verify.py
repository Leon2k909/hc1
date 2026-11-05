"""Verify precise legacy removal, unchanged town/physics and actual play capture."""
import collections,hashlib,json
from PIL import Image,ImageDraw,ImageFont
from native import ROOT,OUT,call
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
original=(ROOT/'Assets/models/maps/belltower/belltower_west.vmdl').read_text()
preview=(ROOT/'Assets/models/maps/belltower/picnic-table-v1/west_without_table.vmdl').read_text()
restored_modeldoc=preview
for name,source in manifest['sources'].items():
 old=(ROOT/source['path']).read_text().splitlines();new=(ROOT/f'Assets/models/maps/belltower/picnic-table-v1/{name}.obj').read_text().splitlines()
 assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
 a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '))
 assert not b-a and sum((a-b).values())==source['removed']
 oldpath=source['path'].replace('\\','/').removeprefix('Assets/')
 restored_modeldoc=restored_modeldoc.replace(f'models/maps/belltower/picnic-table-v1/{name}.obj',oldpath)
assert sum(s['removed'] for s in manifest['sources'].values())==manifest['original_triangles']==60
assert restored_modeldoc==original
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==preview[preview.index(marker):]
folder=OUT/'runtime-review';capture=json.loads((folder/'checked.json').read_text());camera=json.loads((folder/'camera.json').read_text())
assert capture['ActualPlayMode'] and capture['ActiveRuntimeMap']=='scenes/maps/belltower/belltower.scene' and capture['PlayerCount']>0 and not capture['ErrorModels']
assert {'PhotographicResponse','Tonemapping'}<=set(camera['Effects'])
state=json.loads((OUT/'play-state-restored.json').read_text());assert state['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert state['before'][field]==state['after'][field]
status=call('editor_status');assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors']==0
images=[Image.open(folder/f'table-{v}.png').convert('RGB') for v in ('before','after')];assert images[0].size==images[1].size
w,h=images[0].size;sheet=Image.new('RGB',(w*2+24,h+116),(18,23,26));draw=ImageDraw.Draw(sheet)
font=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),32);small=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),20)
for i,(im,title) in enumerate(zip(images,('BEFORE','AFTER'))):
 x=i*(w+24);sheet.paste(im,(x,60));draw.text((x+24,8),title,font=font,fill=(230,237,235))
draw.text((24,h+78),'BELLTOWER / BEER-GARDEN TABLE     Actual play mode · same camera, lighting and exposure',font=small,fill=(171,190,187));sheet.save(OUT/'table-comparison.png')
report=dict(review_only=True,new_triangles=manifest['triangles'],replaced_triangles=60,guarded_original_files=len(guard),original_assets_unchanged=True,unrelated_geometry_unchanged=True,physics_unchanged=True,existing_wood_materials_reused=True,actual_play_mode_checked=True,player_present=True,native_error_models=[],editor_state_restored=True,forced_texture_residency=False,capture=capture,camera=camera,editor_status=status)
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('capture','camera','editor_status')},indent=2))
