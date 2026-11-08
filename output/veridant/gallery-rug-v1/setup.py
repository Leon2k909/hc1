from pathlib import Path
o=Path('output/veridant/gallery-rug-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_gallery_rug as B').replace('lounge-tables-v1','gallery-rug-v1').replace('lounge_coffee_table','gallery_rug').replace('coffee_table','rug')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","V.floor(old,-640,-300,-500,-260,128.2,'vr_rug')")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","V.floor(original,-170,170,-120,120,0,'vr_rug')")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((470,)):").replace("'Lounge coffee table '","'Gallery woven rug '").replace("f'-390,{y},0'","f'-380,{y},128.2'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.15.49.53.png')
s+='''\nmatdir=OUT/'stage/materials/veridant/gallery-rug-v1';matdir.mkdir(parents=True,exist_ok=True)
for name,tint in [('weave','[0.46 0.40 0.32 1]'),('binding','[0.16 0.13 0.10 1]')]:
    text=(ROOT/'Assets/materials/riverside/folded-tarp-v1/cloth.vmat').read_text().replace('[0.117647 0.27451 0.509804 1]',tint).replace('[0.72 0.72 0.72 0]','[0.98 0.98 0.98 0]')
    (matdir/(name+'.vmat')).write_text(text)
'''
(o/'prepare.py').write_text(s)
