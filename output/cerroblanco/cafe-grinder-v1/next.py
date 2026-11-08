from pathlib import Path
import json
R=Path('C:/sbox-projects/hc1/forked-shooter-main');src=R/'Sources/CerroBlanco/gallery-vase-v1/build.py';dest=R/'Sources/CerroBlanco/east-hall-vase-v2';dest.mkdir(exist_ok=True)
s=src.read_text().replace('gallery-vase-v1','east-hall-vase-v2').replace('gallery_vase_v1','east_hall_vase_v2').replace('(700,-300)','(1100,-820)').replace('(700,-300,40)','(1100,-820,40)')
(dest/'build.py').write_text(s)
o=R/'output/cerroblanco/east-hall-vase-v2';o.mkdir(exist_ok=True)
for n in ['import.json','compile.json','show.json','restore.json']:
 (o/n).write_text((R/'output/cerroblanco/gallery-vase-v1'/n).read_text().replace('gallery-vase-v1','east-hall-vase-v2'))
(o/'capture.py').write_text((R/'output/cerroblanco/gallery-vase-v1/capture.py').read_text().replace('-342,-658,64','-862,-1058,64'))
(o/'compile-grinder.json').write_text(json.dumps({'path':'models/maps/cerroblanco/cerroblanco_fitout_fine.vmdl'}))
