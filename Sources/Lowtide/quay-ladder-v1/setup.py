from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3]
HERE=Path(__file__).parent
OUT=ROOT/'output/lowtide/quay-ladder-v1';OUT.mkdir(parents=True,exist_ok=True)
ARES=ROOT/'Sources/Ares/observation-sign-v1'
(HERE/'native.py').write_text((ARES/'native.py').read_text().replace('output/ares/observation-sign-v1','output/lowtide/quay-ladder-v1').replace('ares-observation-sign','lowtide-quay-ladder'))
data=json.loads((ROOT/'Assets/scenes/maps/Lowtide/lowtide.scene').read_text())
print('Scene roots:',[n.get('Name') for n in data['GameObjects']])
capture=(ARES/'baseline.cs.txt').read_text().replace('output/ares/observation-sign-v1','output/lowtide/quay-ladder-v1').replace('Assets/scenes/maps/Ares/ares.scene','Assets/scenes/maps/Lowtide/lowtide.scene').replace('name.StartsWith("Ares")','name=="Lowtide"')
capture=capture.replace('=="models/maps/ares/ares_hall.vmdl"','=="models/maps/lowtide/lowtide_east.vmdl"').replace('=="models/maps/ares/ares_reactor.vmdl"','=="models/maps/lowtide/lowtide_west.vmdl"')
capture=capture.replace('tone.ExposureCompensation=2.2f','tone.ExposureCompensation=2.4f')
(HERE/'baseline.cs.txt').write_text(capture)
views=[dict(name='ladder',eye=[85,-1535,-28],target=[236,-1450,-55],fov=77),dict(name='landing',eye=[158,-1515,40],target=[240,-1450,-6],fov=65)]
(OUT/'capture-config.json').write_text(json.dumps(dict(views=views,variants=['before']),indent=2))
