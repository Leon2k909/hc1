from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');d=R/'Sources/CerroBlanco/south-gallery-vase-v1';d.mkdir(exist_ok=True);o=R/'output/cerroblanco/south-gallery-vase-v1';o.mkdir(exist_ok=True)
s=(R/'Sources/CerroBlanco/gallery-vase-v1/build.py').read_text().replace('gallery-vase-v1','south-gallery-vase-v1').replace('gallery_vase_v1','south_gallery_vase_v1').replace('(700,-300)','(250,-1300)').replace('(700,-300,40)','(250,-1300,40)');(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(o/n).write_text((R/'output/cerroblanco/gallery-vase-v1'/n).read_text().replace('gallery-vase-v1','south-gallery-vase-v1'))
(o/'capture.py').write_text((R/'output/cerroblanco/gallery-vase-v1/capture.py').read_text().replace('-342,-658,64','-1342,-208,64'))
