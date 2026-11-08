from pathlib import Path
o=Path('output/veridant/kiosk-service-door-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_kiosk_service_door as B').replace('lounge-tables-v1','kiosk-service-door-v1').replace('lounge_coffee_table','kiosk_service_door').replace('coffee_table','door').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","V.box(old,-320.5,-319.8,-32,12,128,204,'vr_dark')")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","V.box(original,-.7,0,-22,22,0,76,'vr_dark')")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((319.8,)):").replace("'Lounge coffee table '","'Kiosk closed service door '").replace("f'-390,{y},0'","f'-10,{y},128'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.15.21.44.png')
(o/'prepare.py').write_text(s)
