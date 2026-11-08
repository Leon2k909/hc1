from pathlib import Path
o=Path('output/veridant/terrace-flag-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_terrace_flag as B').replace('lounge-tables-v1','terrace-flag-v1').replace('lounge_coffee_table','terrace_flag').replace('coffee_table','flag').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.flag(old,(-514,413),200,z0=128);old.polygons={k:v for k,v in old.polygons.items() if k=='vr_print'}")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.flag(original,(0,0),200,z0=0)")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((514,)):").replace("'Lounge coffee table '","'Terrace folded flag '").replace("f'-390,{y},0'","f'413,{y},128'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.14.32.48.png')
(o/'prepare.py').write_text(s)
