from pathlib import Path
o=Path('output/veridant/kiosk-wall-lights-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_kiosk_wall_light as B').replace('lounge-tables-v1','kiosk-wall-lights-v1').replace('lounge_coffee_table','kiosk_wall_light').replace('coffee_table','light').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","for n in (-50,30):P.wall_washer(old,'Kiosk lamp '+str(n),(-320,n,198),(1,0),220,light=False,size=(7,4),rise=-14)")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.wall_washer(original,'Reusable original',(0,0,0),(1,0),light=False,size=(7,4))")
s=s.replace("for i,y in enumerate((420,580)):","for i,x in enumerate((-50,30)):").replace("'Lounge coffee table '","'Kiosk recessed wall light '").replace("f'-390,{y},0'","f'{x},320,198'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.15.25.15.png')
(o/'prepare.py').write_text(s)
