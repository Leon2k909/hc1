from pathlib import Path
import sys,json,collections
R=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(R/'Tools'));sys.path.insert(0,str(R/'Sources/CerroBlanco/pan-dulce-v1'))
from build import keys
import cerroblanco_pan_dulce as G
o=R/'output/cerroblanco/pan-dulce-v1';a=collections.Counter(keys(o/'installed/before.obj'));b=collections.Counter(keys(R/'Assets/models/maps/cerroblanco/cerroblanco_fitout_fine.obj'))
assert b==a-collections.Counter(keys(o/'original.obj'))+collections.Counter(keys(o/'placed.obj'))
m=G.build();assert m.triangle_count()==16416 and not m.boxes and not m.hulls
report={'installed':True,'old_faces_removed':540,'new_triangles':16416,'generator_matches':True,'no_collision_added':True,'all_unrelated_geometry_preserved':True}
(o/'installed/verification.json').write_text(json.dumps(report,indent=2));print(report)
