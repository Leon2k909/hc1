from pathlib import Path
import collections,json
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/north-gallery-vase-v1'
s=(R/'Sources/CerroBlanco/gallery-vase-v1/prepare-install.py').read_text().replace('gallery-vase-v1','north-gallery-vase-v1').replace("Path(__file__).with_name('build.py')","(ROOT/'Sources/CerroBlanco/north-gallery-vase-v1/build.py')")
(o/'prepare-install.py').write_text(s);(o/'install.json').write_text((R/'output/cerroblanco/gallery-vase-v1/install.json').read_text().replace('gallery-vase-v1','north-gallery-vase-v1'))
p=R/'Tools/cerroblanco_parts.py';p.write_text(p.read_text().replace('(-880,650,40))','(-880,650,40),(1480,120,40))'))
