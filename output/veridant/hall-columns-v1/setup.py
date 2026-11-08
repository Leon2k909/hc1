from pathlib import Path
p=Path('output/veridant/lounge-tables-v1/prepare.py').read_text()
p=p.replace('lounge-tables-v1','hall-columns-v1').replace('lounge_coffee_table_v1','veridant_hall_columns_v1').replace('lounge_coffee_table_original_v1','veridant_hall_column_original_v1').replace('veridant_lounge_table as B','veridant_hall_columns as B').replace('base_without_tables_','base_without_columns_')
a=p.index('for c in [');b=p.index('V.configure(old)',a)
p=p[:a]+"for e in (100,340,580):P.cylinder(old,(e,-510),14,0,112,'vr_stone',16)\n"+p[b:]
a=p.index('P.cylinder(original,');b=p.index(';V.configure(original)',a)
p=p[:a]+"P.cylinder(original,(0,0),14,0,112,'vr_stone',16)"+p[b:]
p=p.replace('coffee_table_original','column_original').replace('coffee_table','columns')
a=p.index('for i,y in enumerate');b=p.index("(OUT/'before.png')",a)
p=p[:a]+"(OUT/'spawn.json').write_text(json.dumps({'model':SHARED+'/columns.vmdl','name':'Operations hall smooth stone columns','position':'0,0,0'}))\n"+p[b:]
p=p.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.18.35.27.png')
Path('output/veridant/hall-columns-v1/prepare.py').write_text(p)
