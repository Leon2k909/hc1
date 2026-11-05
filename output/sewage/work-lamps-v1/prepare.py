from pathlib import Path
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main')
OUT=ROOT/'output/sewage/work-lamps-v1';HERE=ROOT/'Sources/Sewage/work-lamps-v1'
(OUT/'native.py').write_text((ROOT/'output/sewage/pipe-flanges-v1/native.py').read_text().replace('output/sewage/pipe-flanges-v1','output/sewage/work-lamps-v1'),encoding='utf-8')
(HERE/'import.cs.txt').write_text((ROOT/'Sources/Sewage/pipe-flanges-v1/import.cs.txt').read_text().replace('pipe-flanges-v1','work-lamps-v1'),encoding='utf-8')
source=(ROOT/'Sources/Sewage/valve-wheels-v1/capture.cs.txt').read_text(encoding='utf-8')
source=source.replace('output/sewage/valve-wheels-v1','output/sewage/work-lamps-v1')
source=source.replace('models/maps/sewage/valve-wheels-v1/wheels.vmdl','models/maps/sewage/work-lamps-v1/lamps.vmdl')
source=source.replace('models/maps/sewage/valve-wheels-v1/base_pipework.vmdl','models/maps/sewage/work-lamps-v1/base_details.vmdl')
source=source.replace('models/maps/sewage/sewage_pipework.vmdl','models/maps/sewage/sewage_details.vmdl')
source=source.replace('Waterworks pipework','Waterworks details')
source=source.replace('new Vector3(-538f,852f,215f)','new Vector3(-200f,620f,225f)')
source=source.replace('new Vector3(-624f,953f,195f)','new Vector3(-110f,680f,205f)')
(HERE/'capture.cs.txt').write_text(source,encoding='utf-8')
for model in ('base_details','lamps'):
    (OUT/(model+'.json')).write_text('{"path":"models/maps/sewage/work-lamps-v1/'+model+'.vmdl"}')
