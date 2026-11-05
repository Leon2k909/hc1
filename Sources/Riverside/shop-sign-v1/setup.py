from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;prior=ROOT/'Sources/Riverside/register-v1'
def rename(s):return s.replace('C:/sbox-projects/hc1/register-review','C:/sbox-projects/hc1/shop-sign-review').replace('register-v1','shop-sign-v1').replace('legacy_register.vmdl','legacy_shop_sign.vmdl').replace('store_without_register','store_without_shop_sign').replace('register.vmdl','shop_sign.vmdl')
(HERE/'import.cs.txt').write_text(rename((prior/'import.cs.txt').read_text(encoding='utf-8')),encoding='utf-8')
(HERE/'native.py').write_text(rename((prior/'native.py').read_text(encoding='utf-8')),encoding='utf-8')
s=rename((prior/'isolated-review.cs.txt').read_text(encoding='utf-8'))
s=s.replace('new Vector3(-25,-27,22)','new Vector3(-210,-130,110)').replace('new Vector3(0,0,5)','new Vector3(0,0,44)').replace('FieldOfView=38','FieldOfView=51')
s=s.replace('new Vector3(-30,-40,55),150','new Vector3(-140,-170,170),550').replace('new Vector3(20,30,35),130','new Vector3(160,160,140),480')
(HERE/'isolated-review.cs.txt').write_text(s,encoding='utf-8')
s=rename((prior/'runtime-review.cs.txt').read_text(encoding='utf-8'))
s=s.replace('new Vector3(935,-120,60)','new Vector3(514,-220,150)').replace('new Vector3(902,-153,90)','new Vector3(310,-320,85)').replace('new Vector3(935,-120,65.7f)','new Vector3(514,-220,200)').replace('camera.FieldOfView=38','camera.FieldOfView=55').replace('frame<120','frame<80')
(HERE/'runtime-review.cs.txt').write_text(s,encoding='utf-8')
(HERE/'capture.py').write_text((prior/'capture.py').read_text(encoding='utf-8'),encoding='utf-8')
