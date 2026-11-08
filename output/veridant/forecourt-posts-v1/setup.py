from pathlib import Path
o=Path('output/veridant/forecourt-posts-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_forecourt_post as B').replace('lounge-tables-v1','forecourt-posts-v1').replace('lounge_coffee_table','forecourt_lamp_post').replace('coffee_table','post').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","for c in [(1500,-640),(1500,950),(1820,150)]:\n    P.cylinder(old,c,4.5,0,10,'vr_steel',10,top='vr_steel');P.cylinder(old,c,2.2,10,124,'vr_steel',8)")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.lantern_post(original,'Reusable original forecourt lantern',(0,0,0),140,light=False)")
s=s.replace("for i,y in enumerate((420,580)):","for i,(x,y) in enumerate([(-640,-1500),(950,-1500),(150,-1820)]):").replace("'Lounge coffee table '","'Forecourt tapered lamp post '").replace("f'-390,{y},0'","f'{x},{y},0'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.15.12.40.png')
(o/'prepare.py').write_text(s)
