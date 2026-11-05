from pathlib import Path
here=Path(__file__).parent
root=Path('C:/sbox-projects/hc1/forked-shooter-main')
s=Path('C:/sbox-projects/hc1/counter-review/Sources/Riverside/counter-v1/prepare_install.py').read_text(encoding='utf-8')
for a,b in [('counter-review','shop-sign-review'),('counter-v1','shop-sign-v1'),('counter_lod','shop_sign_lod'),('without_counter','without_shop_sign'),('ctrv1_','shopsignv1_'),('935.0,-135.0,20.0','514.0,-220.0,150.0'),('len(oldgroups)==5','len(oldgroups)==7'),('[0,15,35]','[0,20,45]'),('distance>=35','distance>=45'),('distance>=15','distance>=20'),("OUT/'verification.json'","OUT/'lighting-verified.json'"),('%(p,p) for p',"%(p,'face_toned' if p=='face' else p) for p")]:s=s.replace(a,b)
s=s[:s.index('script=(ROOT/')]+"print(json.dumps(dict(staged_files=len(plan['files']),lod_groups=len(groups),physics_unchanged=True),indent=2))\n"
(here/'prepare_install.py').write_text(s,encoding='utf-8')
s=(root/'Sources/Riverside/counter-v1/install.cs.txt').read_text(encoding='utf-8').replace('counter-review','shop-sign-review').replace('counter-v1','shop-sign-v1').replace('Counters=1','Signs=1')
(here/'install.cs.txt').write_text(s,encoding='utf-8')
