from pathlib import Path
import json,hashlib,re
import numpy as np
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shop-sign-v1';MAT=REVIEW/'Assets/materials/riverside/shop-sign-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());r=json.loads((OUT/'lighting-runtime.json').read_text());native=json.loads((OUT/'lighting-materials.json').read_text())
assert r['ActualPlayMode'] and r['PlayerCount']>0 and not r['ErrorModels'] and r['NoExtraLights'] and r['OnlySignLightEdited'] and r['CameraEffectsUnchanged']
assert abs(r['OriginalIntensity']-1)<1e-5 and abs(r['TonedIntensity']-.2)<1e-5 and r['Radius']==420
assert native['AllMaterialsLoaded'] and native['PrintedFaceHasNoEmission'] and native['LampsRemainLit']
assert json.loads((OUT/'lighting-state-restored.json').read_text())['restored']
saved=json.loads((OUT/'lighting-saved-scene.json').read_text());assert saved['unchanged']
baseline=json.loads((OUT/'lighting-geometry-baseline.json').read_text());assert all(sha(REVIEW/p)==h for p,h in baseline.items())
assert [x['Triangles'] for x in r['Bright']['Meshes']]==[9016,5548,2248]==[x['Triangles'] for x in r['Toned']['Meshes']]
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert all(sha(ROOT/p)==h for p,h in m['files'].items()) and all(sha(ROOT/p)==h for p,h in m['external_files'].items())
face=(MAT/'face_toned.vmat').read_text(encoding='utf-8');assert 'F_SELF_ILLUM' not in face and '[0.72 0.72 0.72 0]' in face
def brightness(path):return float(re.search(r'g_flSelfIllumBrightness\s*"([^"]+)"',path.read_text(encoding='utf-8'))[1])
assert brightness(MAT/'bulb.vmat')==1 and brightness(MAT/'face_bright.vmat')==4.5
assert brightness(ROOT/'Assets/materials/riverside/rs_lamp_warm.vmat')==6
before=Image.open(OUT/'lighting-before.png').convert('RGB');after=Image.open(OUT/'lighting-after.png').convert('RGB')
# Reject the GPU error-mask pattern encountered during an earlier hot reload.
a=np.asarray(after);magenta=(a[:,:,0]>200)&(a[:,:,2]>130)&(a[:,:,1]<np.minimum(a[:,:,0],a[:,:,2])*.8)
assert int(magenta.sum())<100
# This fixed polygon lies inside the sign face at the unchanged review camera.
mask=Image.new('1',before.size,0);ImageDraw.Draw(mask).polygon([(317,441),(935,296),(974,484),(301,577)],fill=1);mask=np.asarray(mask,bool)
def highlights(im):
    q=np.asarray(im);return float(((q.min(2)>215)&(q.max(2)>248)&mask).sum()/mask.sum())
hot_before=highlights(before);hot_after=highlights(after);assert hot_after<hot_before*.5
sheet=Image.new('RGB',(1600,692),'#111416');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
for x,image,title in [(0,before,'PREVIOUS GLARE'),(800,after,'REVISED LIGHTING')]:
    draw.text((x+28,15),title,font=font,fill='#eeeeea');draw.text((x+28,51),'Actual play | same camera settings',font=small,fill='#aeb8ba');sheet.paste(image.resize((800,600),Image.Resampling.LANCZOS),(x,92))
sheet.save(OUT/'lighting-comparison.png')
plan=json.loads((OUT/'lighting-plan.json').read_text());plan.update(face_brightness_after=0.0,face_is_printed_non_emissive=True,face_roughness_after=.72,saved_scene_hash=saved['before'])
(OUT/'lighting-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
report=dict(preview_only=True,actual_play_verified=True,geometry_unchanged=True,printed_face_emission=0,bulb_brightness=1,floodlight_intensity=.2,face_roughness=.72,camera_settings_unchanged=True,no_extra_lights=True,only_sign_light_edited=True,saved_scene_unchanged=True,editor_state_restored=True,error_models=0,near_white_highlight_fraction_before=hot_before,near_white_highlight_fraction_after=hot_after,magenta_error_pixels=int(magenta.sum()))
(OUT/'lighting-verified.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))
