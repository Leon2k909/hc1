from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/tower-vents-v1';HERE=ROOT/'Sources/Sewage/tower-vents-v1'
(OUT/'native.py').write_text((ROOT/'output/sewage/pipe-flanges-v1/native.py').read_text().replace('output/sewage/pipe-flanges-v1','output/sewage/tower-vents-v1'),encoding='utf-8')
source=(ROOT/'Sources/Sewage/valve-wheels-v1/capture.cs.txt').read_text(encoding='utf-8')
source=source.replace('output/sewage/valve-wheels-v1','output/sewage/tower-vents-v1')
source=source.replace('models/maps/sewage/valve-wheels-v1/wheels.vmdl','models/maps/sewage/tower-vents-v1/vents.vmdl')
source=source.replace('models/maps/sewage/valve-wheels-v1/base_pipework.vmdl','models/maps/sewage/tower-vents-v1/base_tower.vmdl')
source=source.replace('models/maps/sewage/sewage_pipework.vmdl','models/maps/sewage/sewage_tower.vmdl')
source=source.replace('Waterworks pipework','Waterworks tower')
source=source.replace('new Vector3(-538f,852f,215f)','new Vector3(400f,-15f,864f)')
source=source.replace('new Vector3(-624f,953f,195f)','new Vector3(500f,85f,819f)')
(HERE/'capture.cs.txt').write_text(source,encoding='utf-8')
for model in ('base_tower','vents'):
    (OUT/(model+'.json')).write_text('{"path":"models/maps/sewage/tower-vents-v1/'+model+'.vmdl"}')
