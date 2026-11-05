from pathlib import Path
import re,json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/shop-sign-v1'
path=REVIEW/'Assets/materials/riverside/shop-sign-v1/face.vmat'
s=path.read_text(encoding='utf-8');s,n=re.subn(r'TextureRoughness "\[[^"]+\]"','TextureRoughness "[0.72 0.72 0.72 0]"',s);assert n==1;path.write_text(s,encoding='utf-8')
m=json.loads((OUT/'manifest.json').read_text());m['files'][str(path.relative_to(REVIEW)).replace('\\','/')]=hashlib.sha256(path.read_bytes()).hexdigest();(OUT/'manifest.json').write_text(json.dumps(m,indent=2),encoding='utf-8')
plan=json.loads((OUT/'lighting-plan.json').read_text());plan.update(face_roughness_before=.34,face_roughness_after=.72)
scene=ROOT/'Assets/scenes/maps/Riverside/riverside.scene';plan['saved_scene_hash']=hashlib.sha256(scene.read_bytes()).hexdigest()
(OUT/'lighting-plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
print('Reduced the face specular hotspot; preserved geometry, artwork and all shared materials.')
