from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
s=(ROOT/'Tools/belltower_bistro_tables.py').read_text().replace('bistro-table-v2/bistro_table.vmdl','dish-lamp-v2/wall_lantern.vmdl').replace('Bistro tables','Suspended lamps').replace('Bistro table','Suspended lamp').replace('bistro_tables','dish_lamps').replace('bistro_table','dish_lamp')
(ROOT/'Tools/belltower_dish_lamps.py').write_text(s)
for name in ('install.cs.txt','delete-old.cs.txt','finish_install.py'):
    s=(ROOT/'Sources/Belltower/bistro-table-v2'/name).read_text().replace('bistro-table-v2','dish-lamp-v2').replace('bistro_table.vmdl','wall_lantern.vmdl').replace('Bistro tables','Suspended lamps').replace('tables','lamps').replace('Tables','Lamps').replace('table','lamp').replace('Table','Lamp')
    s=s.replace('!=7','!=10').replace('all 7','all 10').replace('Installed=7','Installed=10').replace('3038','3560')
    (HERE/name).write_text(s)
print('Prepared lamp module and native scripts.')
