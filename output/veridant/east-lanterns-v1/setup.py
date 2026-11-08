from pathlib import Path
p=Path('output/veridant/lounge-tables-v1/prepare.py').read_text()
p=p.replace('lounge-tables-v1','east-lanterns-v1').replace('lounge_coffee_table_v1','east_terrace_lantern_v1').replace('lounge_coffee_table_original_v1','east_terrace_lantern_original_v1').replace('veridant_lounge_table as B','veridant_east_lantern as B').replace('base_without_tables_','base_without_east_lanterns_')
a=p.index('for c in [');b=p.index('V.configure(old)',a)
p=p[:a]+"for i,base in enumerate(B.BASES):P.lantern_post(old,'Original east '+str(i),base,96,light=False)\n"+p[b:]
a=p.index('P.cylinder(original,');b=p.index(';V.configure(original)',a)
p=p[:a]+"P.lantern_post(original,'Original east',(0,0,0),96,light=False)"+p[b:]
p=p.replace('coffee_table_original','lantern_original').replace('coffee_table','lantern')
a=p.index('for i,y in enumerate');b=p.index("(OUT/'before.png')",a)
p=p[:a]+"(OUT/'spawn.json').write_text(json.dumps({'model':SHARED+'/lantern.vmdl','name':'East terrace framed lanterns','position':'0,0,0'}))\n"+p[b:]
p=p.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.18.29.56.png')
Path('output/veridant/east-lanterns-v1/prepare.py').write_text(p)
