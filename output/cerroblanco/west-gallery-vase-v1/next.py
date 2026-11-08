from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/west-gallery-vase-v1'
s=(R/'Sources/CerroBlanco/gallery-vase-v1/prepare-install.py').read_text().replace('gallery-vase-v1','west-gallery-vase-v1').replace("Path(__file__).with_name('build.py')","(ROOT/'Sources/CerroBlanco/west-gallery-vase-v1/build.py')")
(o/'prepare-install.py').write_text(s);(o/'install.json').write_text((R/'output/cerroblanco/gallery-vase-v1/install.json').read_text().replace('gallery-vase-v1','west-gallery-vase-v1'))
p=R/'Tools/cerroblanco_parts.py';p.write_text(p.read_text().replace('(250,-1300,40))','(250,-1300,40),(-880,650,40))'))
d=R/'Sources/CerroBlanco/north-gallery-vase-v1';d.mkdir(exist_ok=True);out=R/'output/cerroblanco/north-gallery-vase-v1';out.mkdir(exist_ok=True)
s=(R/'Sources/CerroBlanco/gallery-vase-v1/build.py').read_text().replace('gallery-vase-v1','north-gallery-vase-v1').replace('gallery_vase_v1','north_gallery_vase_v1').replace('(700,-300)','(1480,120)').replace('(700,-300,40)','(1480,120,40)');(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(out/n).write_text((R/'output/cerroblanco/gallery-vase-v1'/n).read_text().replace('gallery-vase-v1','north-gallery-vase-v1'))
(out/'capture.py').write_text((R/'output/cerroblanco/gallery-vase-v1/capture.py').read_text().replace('-342,-658,64','78,-1438,64'))
