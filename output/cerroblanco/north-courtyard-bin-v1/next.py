from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/north-courtyard-bin-v1'
s=(R/'Sources/CerroBlanco/courtyard-bin-v1/prepare-install.py').read_text().replace('courtyard-bin-v1','north-courtyard-bin-v1').replace("Path(__file__).with_name('build.py')","(ROOT/'Sources/CerroBlanco/north-courtyard-bin-v1/build.py')")
(o/'prepare-install.py').write_text(s);(o/'install.json').write_text((R/'output/cerroblanco/courtyard-bin-v1/install.json').read_text().replace('courtyard-bin-v1','north-courtyard-bin-v1'))
p=R/'Tools/cerroblanco_parts.py';p.write_text(p.read_text().replace('if (e,n)==(380,-650):','if (e,n) in ((380,-650),(-150,50)):'))
d=R/'Sources/CerroBlanco/west-gallery-vase-v1';d.mkdir(exist_ok=True);out=R/'output/cerroblanco/west-gallery-vase-v1';out.mkdir(exist_ok=True)
s=(R/'Sources/CerroBlanco/gallery-vase-v1/build.py').read_text().replace('gallery-vase-v1','west-gallery-vase-v1').replace('gallery_vase_v1','west_gallery_vase_v1').replace('(700,-300)','(-880,650)').replace('(700,-300,40)','(-880,650,40)');(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(out/n).write_text((R/'output/cerroblanco/gallery-vase-v1'/n).read_text().replace('gallery-vase-v1','west-gallery-vase-v1'))
(out/'capture.py').write_text((R/'output/cerroblanco/gallery-vase-v1/capture.py').read_text().replace('-342,-658,64','608,922,64'))
