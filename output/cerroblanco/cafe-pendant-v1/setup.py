from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');d=R/'Sources/CerroBlanco/cafe-pendant-v1';d.mkdir(exist_ok=True);o=R/'output/cerroblanco/cafe-pendant-v1'
q=(R/'Sources/CerroBlanco/queue-posts-v1/model.py').read_text();lathe=q[q.index('    def lathe('):q.index('    for lane in LANES:')]
model='import math\nimport numpy as np\nimport map_kit as K\nimport riverdale_parts as P\ndef build():\n    m=K.Model()\n'+lathe+'''    lathe([(5.35,108.1),(6.1,108.1),(6.4,108.0),(6.52,108.18),(6.42,108.42),(6.05,109.1),(5.5,110.4),(4.9,111.9),(4.05,113.7),(3.2,115.2),(2.3,116.8),(1.4,118.2),(.65,119.2),(.6,120),(0,120)],'cbf_track',(620,615),48)
    lathe([(5.35,108.1),(5.9,108.4),(5.55,109.2),(5.0,110.6),(4.4,112.1),(3.55,113.9),(2.7,115.4),(1.8,117),(1.0,118.2),(.45,119.1),(0,119.1)],'cbf_plastic',(620,615),48)
    m.material_overrides.update({k:'materials/cerroblanco/fitout/'+k+'.vmat' for k in ('cbf_track','cbf_plastic')})
    m.tile_overrides.update({k:24. for k in m.polygons});return m
''';(d/'model.py').write_text(model)
s=(R/'Sources/CerroBlanco/cafe-display-v1/build.py').read_text().replace('cafe-display-v1','cafe-pendant-v1').replace('cafe_display_v1','cafe_pendant_v1');a=s.index('    old=K.Model();');b=s.index('    targets=',a)
s=s[:a]+'''    old=K.Model();F.lathe(old,'cbf_track',(620,615,108),[(6.5,0),(5.8,3),(2.4,10),(.6,12)],sides=16)
    old.tile_overrides['cbf_track']=24.;K.write_obj(OUT/'original.obj',old,'old_shade')
'''+s[b:];s=s.replace('removed==22','removed==110');(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(o/n).write_text((R/'output/cerroblanco/cafe-display-v1'/n).read_text().replace('cafe-display-v1','cafe-pendant-v1'))
(o/'capture.py').write_text((R/'output/cerroblanco/cafe-display-v1/capture.py').read_text().replace('515,-655,64','574,-606,103').replace("'angles':'8,0,0'","'angles':'-13,-20,0'"))
