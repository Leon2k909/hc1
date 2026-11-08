from pathlib import Path
o=Path('output/veridant/terrace-tarp-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_terrace_tarp as B').replace('lounge-tables-v1','terrace-tarp-v1').replace('lounge_coffee_table','terrace_tarp').replace('coffee_table','tarp')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.tarp_over(old,(762,-146),(762,-52),234,(-1,0),drop_out=30,drop_in=27,seed=2,rail=1.5)")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.tarp_over(original,(0,0),(0,94),42,(-1,0),drop_out=30,drop_in=27,seed=2,rail=1.5)")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((-762,)):").replace("'Lounge coffee table '","'Terrace woven canvas '").replace("f'-390,{y},0'","f'-146,{y},192'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.15.41.48.png')
s=s.replace("original=K.Model();", "original=K.Model();")
# Add dedicated material to the same native-import staging tree.
s+='''\nmat=OUT/'stage/materials/veridant/terrace-tarp-v1/canvas.vmat';mat.parent.mkdir(parents=True,exist_ok=True)
mat.write_text((ROOT/'Assets/materials/riverside/folded-tarp-v1/cloth.vmat').read_text().replace('[0.117647 0.27451 0.509804 1]','[0.24 0.26 0.22 1]').replace('[0.72 0.72 0.72 0]','[0.86 0.86 0.86 0]'))
'''
(o/'prepare.py').write_text(s)
