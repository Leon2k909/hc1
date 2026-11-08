from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/east-hall-vase-v2'
s=(R/'Sources/CerroBlanco/gallery-vase-v1/prepare-install.py').read_text().replace('gallery-vase-v1','east-hall-vase-v2')
s=s.replace("Path(__file__).with_name('build.py')","(ROOT/'Sources/CerroBlanco/east-hall-vase-v2/build.py')")
(o/'prepare-install.py').write_text(s)
(o/'install.json').write_text((R/'output/cerroblanco/gallery-vase-v1/install.json').read_text().replace('gallery-vase-v1','east-hall-vase-v2'))
p=R/'Tools/cerroblanco_parts.py';s=p.read_text().replace('if (e,n,h)==(700,-300,40):','if (e,n,h) in ((700,-300,40),(1100,-820,40)):');p.write_text(s)
