from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');OUT=ROOT/'output/sewage/tower-deck-v1';HERE=ROOT/'Sources/Sewage/tower-deck-v1'
(OUT/'native.py').write_text((ROOT/'output/sewage/tower-rails-v1/native.py').read_text().replace('output/sewage/tower-rails-v1','output/sewage/tower-deck-v1'))
(HERE/'import.cs.txt').write_text((ROOT/'Sources/Sewage/tower-rails-v1/import.cs.txt').read_text().replace('tower-rails-v1','tower-deck-v1'))
s=(ROOT/'Sources/Sewage/tower-rails-v1/capture.cs.txt').read_text()
s=s.replace('output/sewage/tower-rails-v1','output/sewage/tower-deck-v1').replace('models/maps/sewage/tower-rails-v1/rails.vmdl','models/maps/sewage/tower-deck-v1/deck.vmdl')
s=s.replace('models/maps/sewage/tower-rails-v1/base_tower.vmdl','models/maps/sewage/tower-deck-v1/base_tower.vmdl').replace('models/maps/sewage/tower-vents-v1/base_tower.vmdl','models/maps/sewage/tower-rails-v1/base_tower.vmdl')
s=s.replace('new Vector3(650f,-140f,840f)','new Vector3(650f,-50f,855f)').replace('new Vector3(760f,-27f,813f)','new Vector3(745f,-25f,791.5f)')
(HERE/'capture.cs.txt').write_text(s)
for name in ('base_tower','deck'):(OUT/(name+'.json')).write_text('{"path":"models/maps/sewage/tower-deck-v1/'+name+'.vmdl"}')
