from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=ROOT/'output/reefhall/pump-v1';OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene').read_text())
print([x.get('Name') for x in data['GameObjects']])
old=ROOT/'Sources/Lowtide/quay-ladder-v1'
(HERE/'native.py').write_text((old/'native.py').read_text().replace('output/lowtide/quay-ladder-v1','output/reefhall/pump-v1').replace('lowtide-quay-ladder','reefhall-pump'))
capture=(old/'baseline.cs.txt').read_text().replace('output/lowtide/quay-ladder-v1','output/reefhall/pump-v1').replace('Assets/scenes/maps/Lowtide/lowtide.scene','Assets/scenes/maps/ReefHall/reefhall.scene')
capture=capture.replace('"Sun","Sky","Fog","Look","Lights","Reflection Probes"','"Ambient","Sun","Sky","Fog","Look","Lights","Reflection Probes"').replace('name=="Lowtide"','name=="Aquarium"')
capture=capture.replace('models/maps/lowtide/lowtide_east.vmdl','models/maps/reefhall/reefhall_filter.vmdl').replace('models/maps/lowtide/lowtide_west.vmdl','models/maps/reefhall/reefhall_filter_tanks.vmdl')
capture=capture.replace('tone.ExposureCompensation=2.4f','tone.ExposureCompensation=2.0f')
(HERE/'baseline.cs.txt').write_text(capture)
views=[dict(name='pump',eye=[-485,1480,80],target=[-380,1610,34],fov=55),dict(name='inlet',eye=[-275,1520,64],target=[-375,1610,32],fov=60)]
(OUT/'capture-config.json').write_text(json.dumps(dict(views=views,variants=['before']),indent=2))
