from pathlib import Path
o=Path('output/veridant/fountain-bowl-v1');o.mkdir(parents=True,exist_ok=True)
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text()
s=s.replace('veridant_lounge_table as B','veridant_fountain_bowl as B').replace('lounge-tables-v1','fountain-bowl-v1').replace('lounge_coffee_table','fountain_bowl').replace('coffee_table','fountain_bowl').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.lathe(old,(1600,150),[(10,14),(10,46),(34,52),(30,58),(0,56)],'vr_stone',20)")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.lathe(original,(0,0),[(10,14),(10,46),(34,52),(30,58),(0,56)],'vr_stone',20)")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((-1600,)):").replace("'Lounge coffee table '","'Forecourt carved fountain bowl '").replace("f'-390,{y},0'","f'150,{y},0'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.14.28.52.png')
(o/'prepare.py').write_text(s)
