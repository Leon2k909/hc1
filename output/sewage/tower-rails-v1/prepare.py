from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/sewage/tower-rails-v1';HERE=ROOT/'Sources/Sewage/tower-rails-v1'
(OUT/'native.py').write_text((ROOT/'output/sewage/tower-vents-v1/native.py').read_text().replace('output/sewage/tower-vents-v1','output/sewage/tower-rails-v1'))
(HERE/'import.cs.txt').write_text((ROOT/'Sources/Sewage/tower-vents-v1/import.cs.txt').read_text().replace('tower-vents-v1','tower-rails-v1'))
s=(ROOT/'Sources/Sewage/tower-vents-v1/capture.cs.txt').read_text()
s=s.replace('output/sewage/tower-vents-v1','output/sewage/tower-rails-v1').replace('models/maps/sewage/tower-vents-v1/vents.vmdl','models/maps/sewage/tower-rails-v1/rails.vmdl')
s=s.replace('models/maps/sewage/tower-vents-v1/base_tower.vmdl','models/maps/sewage/tower-rails-v1/base_tower.vmdl').replace('models/maps/sewage/sewage_tower.vmdl','models/maps/sewage/tower-vents-v1/base_tower.vmdl')
s=s.replace('new Vector3(400f,-15f,864f)','new Vector3(430f,-50f,846f)').replace('new Vector3(500f,85f,819f)','new Vector3(510f,110f,813f)')
(HERE/'capture.cs.txt').write_text(s)
for name in ('base_tower','rails'):(OUT/(name+'.json')).write_text('{"path":"models/maps/sewage/tower-rails-v1/'+name+'.vmdl"}')
