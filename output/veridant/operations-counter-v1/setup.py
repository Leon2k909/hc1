from pathlib import Path
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_operations_counter as B').replace('lounge-tables-v1','operations-counter-v1').replace('lounge_coffee_table','operations_counter').replace('coffee_table','counter')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.bar_counter(old,(380,-560),(520,-530),128,front='+n')")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.bar_counter(original,(-70,-15),(70,15),0,front='+n')")
s=s.replace('for i,y in enumerate((420,580)):','for i,y in enumerate((-450,)):').replace('Lounge coffee table ','Operations stone counter ').replace("f'-390,{y},0'","f'-545,{y},128'").replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.16.43.22.png')
Path('output/veridant/operations-counter-v1/prepare.py').write_text(s)
