from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/south-gallery-vase-v1'
s=(R/'Sources/CerroBlanco/gallery-vase-v1/prepare-install.py').read_text().replace('gallery-vase-v1','south-gallery-vase-v1').replace("Path(__file__).with_name('build.py')","(ROOT/'Sources/CerroBlanco/south-gallery-vase-v1/build.py')")
(o/'prepare-install.py').write_text(s);(o/'install.json').write_text((R/'output/cerroblanco/gallery-vase-v1/install.json').read_text().replace('gallery-vase-v1','south-gallery-vase-v1'))
p=R/'Tools/cerroblanco_parts.py';s=p.read_text().replace('((700,-300,40),(1100,-820,40))','((700,-300,40),(1100,-820,40),(250,-1300,40))');p.write_text(s)
d=R/'Sources/CerroBlanco/north-courtyard-bin-v1';d.mkdir(exist_ok=True);out=R/'output/cerroblanco/north-courtyard-bin-v1';out.mkdir(exist_ok=True)
s=(R/'Sources/CerroBlanco/courtyard-bin-v1/build.py').read_text().replace('courtyard-bin-v1','north-courtyard-bin-v1').replace('hooded_bin_v1','north_hooded_bin_v1').replace('(380,-650)','(-150,50)').replace('(380,-650,0)','(-150,50,0)');(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(out/n).write_text((R/'output/cerroblanco/courtyard-bin-v1'/n).read_text().replace('courtyard-bin-v1','north-courtyard-bin-v1'))
(out/'capture.py').write_text((R/'output/cerroblanco/gallery-vase-v1/capture.py').read_text().replace('-342,-658,64','-5,205,48').replace("'angles':'14,-45,0'","'angles':'16,-45,0'"))
