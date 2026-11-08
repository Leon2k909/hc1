from pathlib import Path
p=Path('output/veridant/lounge-tables-v1/prepare.py').read_text()
p=p.replace('lounge-tables-v1','cafe-pergola-teak-v1').replace('lounge_coffee_table_v1','veridant_cafe_pergola_teak_v1').replace('lounge_coffee_table_original_v1','veridant_cafe_pergola_original_v1').replace('veridant_lounge_table as B','veridant_cafe_pergola_teak as B').replace('base_without_tables_','base_without_cafe_pergola_').replace('veridant_buildings','veridant_dress')
a=p.index('for c in [');b=p.index('V.configure(old)',a)
p=p[:a]+"B.legacy_into(old,(-600,132.5),254)\n"+p[b:]
a=p.index('P.cylinder(original,');b=p.index(';V.configure(original)',a)
p=p[:a]+"B.legacy_into(original)"+p[b:]
p=p.replace('coffee_table_original','pergola_original').replace('coffee_table','pergola')
a=p.index('for i,y in enumerate');b=p.index("(OUT/'before.png')",a)
p=p[:a]+"(OUT/'spawn.json').write_text(json.dumps({'model':SHARED+'/pergola.vmdl','name':'Cafe pergola teak roof timbers','position':'132.5,600,254'}))\n"+p[b:]
p=p.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.19.07.57.png')
Path('output/veridant/cafe-pergola-teak-v1/prepare.py').write_text(p)
