from pathlib import Path
import json,shutil,re,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shop-sign-v1';MODEL=REVIEW/'Assets/models/maps/riverside/shop-sign-v1';MAT=REVIEW/'Assets/materials/riverside/shop-sign-v1'
reference=MODEL/'bright_reference.vmdl'
if not reference.exists():
    face=(MAT/'face.vmat').read_text(encoding='utf-8');assert 'g_flSelfIllumBrightness "4.5"' in face
    (MAT/'face_bright.vmat').write_text(face,encoding='utf-8')
    reference.write_text((MODEL/'shop_sign.vmdl').read_text(encoding='utf-8').replace('materials/riverside/shop-sign-v1/face.vmat','materials/riverside/shop-sign-v1/face_bright.vmat'),encoding='utf-8')
    for name in ('runtime-review.json','verification.json','in-game-after.png'):
        source=OUT/name
        if source.exists():shutil.copy2(source,OUT/('bright-baseline-'+name))
plan=dict(preview_only=True,face_brightness_before=4.5,face_brightness_after=.65,bulb_brightness_before=6.0,bulb_brightness_after=1.0,point_light_guid='ad251c23-5036-51ff-9ecb-932578dc96f1',point_light_position=[454,-220,210],point_intensity_before=1.0,point_intensity_after=.20,radius=420,global_camera_unchanged=True)
(OUT/'lighting-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
m=json.loads((OUT/'manifest.json').read_text());(OUT/'lighting-geometry-baseline.json').write_text(json.dumps({p:h for p,h in m['files'].items() if 'shop_sign_lod' in p and p.endswith(('.obj','.mtl'))},indent=2),encoding='utf-8')
print(json.dumps(plan,indent=2))
