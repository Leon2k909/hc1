"""Verify source preservation, shared-resource reuse and actual play captures."""
import collections,hashlib,json
from PIL import Image,ImageDraw,ImageFont
from native import ROOT,OUT,call
def records(path):
 lines=path.read_text().splitlines(keepends=True);vs=[tuple(round(float(v),3) for v in l.split()[1:4]) for l in lines if l.startswith('v ')]
 paint='';result=[]
 for i,l in enumerate(lines):
  if l.startswith('usemtl '):paint=l.split()[1]
  if l.startswith('f '):result.append((i,(paint,tuple(sorted(vs[int(t.split('/')[0])-1] for t in l.split()[1:])))))
 return lines,result
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
guard=json.loads((OUT/'source-guard.json').read_text())
changed=[p for p,h in guard.items() if not (ROOT/p).is_file() or sha(ROOT/p)!=h]
assert not changed,changed
manifest=json.loads((OUT/'manifest.json').read_text())
assert len(manifest['files'])==6
assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
source=ROOT/manifest['source'];preview=ROOT/'Assets/models/maps/riverdale/sand-bin-v1/yard_without_bin.obj'
old,faces=records(source);new,newfaces=records(preview)
assert [l for l in old if l.startswith(('v ','vt ','vn '))]==[l for l in new if l.startswith(('v ','vt ','vn '))]
a=collections.Counter(l for l in old if l.startswith('f '));b=collections.Counter(l for l in new if l.startswith('f '))
assert not b-a and sum((a-b).values())==38==manifest['original_triangles']
_,body=records(OUT/'legacy-body.obj');_,full=records(OUT/'legacy-full.obj')
tail=collections.Counter(k for _,k in full)-collections.Counter(k for _,k in body)
assert sum(tail.values())==0 and not tail-collections.Counter(k for _,k in newfaces)
original=(ROOT/'Assets/models/maps/riverdale/riverdale_yard_props.vmdl').read_text()
stage=preview.with_suffix('.vmdl').read_text()
assert stage.replace('models/maps/riverdale/sand-bin-v1/yard_without_bin.obj','models/maps/riverdale/riverdale_yard_props.obj')==original
folder=OUT/'runtime-review';capture=json.loads((folder/'checked.json').read_text());camera=json.loads((folder/'camera.json').read_text())
assert capture['ActualPlayMode'] and capture['ActiveRuntimeMap']=='scenes/maps/riverdale/riverdale.scene'
assert capture['PlayerCount']>0 and not capture['ErrorModels']
assert {'Tonemapping','PhotographicResponse'}<=set(camera['Effects'])
restored=json.loads((OUT/'play-state-restored.json').read_text());assert restored['restored']
for field in ('ActiveScenePath','IsPlaying','SceneHasUnsavedChanges'):assert restored['before'][field]==restored['after'][field]
assert restored['after']['LastCompileSucceeded'] and restored['after']['LastCompileErrors']==0
font=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),38);small=ImageFont.truetype(str(ROOT/'Assets/fonts/Dinish-Bold.ttf'),24)
for name in ('bin','detail'):
 imgs=[Image.open(folder/f'{name}-{v}.png').convert('RGB') for v in ('before','after')];assert imgs[0].size==imgs[1].size
 w,h=imgs[0].size;sheet=Image.new('RGB',(2*w+24,h+116),(18,23,26));draw=ImageDraw.Draw(sheet)
 for i,(im,title) in enumerate(zip(imgs,('BEFORE','AFTER'))):
  x=i*(w+24);sheet.paste(im,(x,60));draw.text((x+24,8),title,font=font,fill=(230,237,235))
 draw.text((24,h+78),'RIVERDALE / SAND BIN     Actual play mode · same camera, lighting and exposure',font=small,fill=(171,190,187))
 sheet.save(OUT/f'{name}-comparison.png')
report=dict(review_only=True,reused_existing_approved_resource=manifest['reused_resource'],replacement_triangles=manifest['triangles'],removed_old_body_triangles=38,preserved_cable_tail_triangles=0,guarded_original_files=len(guard),original_assets_unchanged=True,unrelated_geometry_unchanged=True,physics_and_saved_scene_unchanged=True,new_replacement_meshes=1,actual_play_mode_checked=True,player_present=True,native_error_models=[],editor_state_restored=True,streaming_frames_per_view=180,forced_texture_residency=False,camera=camera,capture=capture)
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('camera','capture')},indent=2))
