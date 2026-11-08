from pathlib import Path
p=Path('output/veridant/lounge-tables-v1/prepare.py').read_text()
p=p.replace('lounge-tables-v1','court-stair-rail-v1').replace('lounge_coffee_table_v1','veridant_court_stair_rail_v1').replace('lounge_coffee_table_original_v1','veridant_court_stair_rail_original_v1').replace('veridant_lounge_table as B','veridant_court_stair_rail as B').replace('base_without_tables_','base_without_court_rail_')
a=p.index('for c in [');b=p.index('V.configure(old)',a)
p=p[:a]+"P.steel_rail(old,[(660,-255),(473,-255)],0,slope=[7,128],clip_to=None,name='Original court rail',style='rails')\nP.rod(old,(473,-255,128),(473,-255,169.2),.7,'vr_steel',6)\n"+p[b:]
a=p.index('P.cylinder(original,');b=p.index(';V.configure(original)',a)
p=p[:a]+"P.steel_rail(original,[(0,0),(-187,0)],0,slope=[7,128],clip_to=None,name='Reusable old court rail',style='rails')"+p[b:]
p=p.replace('coffee_table_original','rail_original').replace('coffee_table','rail')
a=p.index('for i,y in enumerate');b=p.index("(OUT/'before.png')",a)
p=p[:a]+"(OUT/'spawn.json').write_text(json.dumps({'model':SHARED+'/rail.vmdl','name':'Courtyard stair smooth mounted handrail','position':'0,0,0'}))\n"+p[b:]
p=p.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.18.53.00.png')
Path('output/veridant/court-stair-rail-v1/prepare.py').write_text(p)
