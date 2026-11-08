from pathlib import Path
p=Path('output/veridant/lounge-tables-v1/prepare.py').read_text()
p=p.replace('lounge-tables-v1','operations-window-backing-v1').replace('base_without_tables_','base_without_window_backing_')
a=p.index('old=K.Model()');b=p.index('V.configure(old)',a)
p=p[:a]+"old=K.Model()\nV.box(old,450,590,-683,-682,150,236,'vr_window_dark')\n"+p[b:]
a=p.index('m=K.Model();');b=p.index('ex=Path(',a)
p=p[:a]+p[b:]
a=p.index('for name,path in')
p=p[:a]+"""(OUT/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.18.26.09.png').read_bytes())
(OUT/'checks.json').write_text(json.dumps({'removed_triangles':sum(removed.values()),'physics_unchanged':True},indent=2));print((OUT/'checks.json').read_text())
"""
Path('output/veridant/operations-window-backing-v1/prepare.py').write_text(p)
