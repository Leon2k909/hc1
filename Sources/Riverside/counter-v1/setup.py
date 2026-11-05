from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent
prior=ROOT/'Sources/Riverside/register-v1'
def rename(s):return s.replace('C:/sbox-projects/hc1/register-review','C:/sbox-projects/hc1/counter-review').replace('register-v1','counter-v1').replace('legacy_register.vmdl','legacy_counter.vmdl').replace('register.vmdl','counter.vmdl').replace('store_without_register','store_without_counter')
s=rename((prior/'import.cs.txt').read_text());(HERE/'import.cs.txt').write_text(s)
s=rename((prior/'isolated-review.cs.txt').read_text())
s=s.replace('new Vector3(-25,-27,22)','new Vector3(-115,-88,77)').replace('new Vector3(0,0,5)','new Vector3(0,0,21)').replace('FieldOfView=38','FieldOfView=46')
s=s.replace('new Vector3(-30,-40,55),150','new Vector3(-100,-100,125),330').replace('new Vector3(20,30,35),130','new Vector3(80,90,90),320')
(HERE/'isolated-review.cs.txt').write_text(s)
s=rename((prior/'runtime-review.cs.txt').read_text())
s=s.replace('new Vector3(935,-120,60)','new Vector3(935,-135,20)').replace('new Vector3(902,-153,90)','new Vector3(812,-210,92)').replace('new Vector3(935,-120,65.7f)','new Vector3(935,-135,42)').replace('camera.FieldOfView=38','camera.FieldOfView=55')
(HERE/'runtime-review.cs.txt').write_text(s)
(HERE/'capture.py').write_text((prior/'capture.py').read_text())
(HERE/'native.py').write_text(rename((prior/'native.py').read_text()))
