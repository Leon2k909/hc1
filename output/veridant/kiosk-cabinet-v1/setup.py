from pathlib import Path
o=Path('output/veridant/kiosk-cabinet-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_kiosk_cabinet as B').replace('lounge-tables-v1','kiosk-cabinet-v1').replace('lounge_coffee_table','kiosk_cabinet').replace('coffee_table','cabinet').replace('veridant_buildings','veridant_dress')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","V.solid(old,-300,-270,100,160,128,188,{'default':'vr_dark','+z':'vr_steel'},'metal')")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","V.solid(original,-15,15,-30,30,0,60,{'default':'vr_dark','+z':'vr_steel'},'metal')")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((285,)):").replace("'Lounge coffee table '","'Terrace utility cabinet '").replace("f'-390,{y},0'","f'130,{y},128'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.15.16.57.png')
(o/'prepare.py').write_text(s)
