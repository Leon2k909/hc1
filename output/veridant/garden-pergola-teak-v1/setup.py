from pathlib import Path
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_garden_pergola as B').replace('lounge-tables-v1','garden-pergola-teak-v1').replace('lounge_coffee_table','garden_pergola_teak').replace('coffee_table','pergola').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","B.legacy_into(old,(-460,-1240))")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","B.legacy_into(original)")
s=s.replace('for i,y in enumerate((420,580)):','for i,y in enumerate((460,)):').replace('Lounge coffee table ','South garden teak pergola ').replace("f'-390,{y},0'","f'-1240,{y},0'").replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.18.14.16.png')
Path('output/veridant/garden-pergola-teak-v1/prepare.py').write_text(s)
