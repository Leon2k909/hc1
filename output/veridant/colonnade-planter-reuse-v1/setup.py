from pathlib import Path
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_colonnade_planter as B').replace('lounge-tables-v1','colonnade-planter-reuse-v1').replace('lounge_coffee_table','colonnade_planter').replace('coffee_table','planter')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","for e,n in [(-236,4),(-236,36),(-214,4),(-214,36)]:V.box(old,e-10,e+10,n-15,n+15,0,22,{'default':'vr_case_black','+z':'vr_soil'})")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","for e,n in [(-11,-16),(-11,16),(11,-16),(11,16)]:V.box(original,e-10,e+10,n-15,n+15,0,22,{'default':'vr_case_black','+z':'vr_soil'})")
s=s.replace('for i,y in enumerate((420,580)):','for i,y in enumerate((225,)):').replace('Lounge coffee table ','Colonnade bronze planter ').replace("f'-390,{y},0'","f'20,{y},0'").replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.17.01.01.png')
# Original single-line model construction cannot contain an inline compound loop.
s=s.replace("original=K.Model();original.uv_source_name='veridant_buildings';for e,n", "original=K.Model();original.uv_source_name='veridant_buildings'\nfor e,n")
Path('output/veridant/colonnade-planter-reuse-v1/prepare.py').write_text(s)
