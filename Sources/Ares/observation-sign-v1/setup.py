from pathlib import Path
import json,sys
ROOT=Path(__file__).resolve().parents[3]
OUT=ROOT/'output/ares/observation-sign-v1'
OUT.mkdir(parents=True,exist_ok=True)
src=ROOT/'Sources/Ares/interior-v1'
native=(src/'native.py').read_text().replace("output/ares/interior-v1","output/ares/observation-sign-v1").replace("ares-interior","ares-observation-sign")
(Path(__file__).parent/'native.py').write_text(native)
capture=(src/'capture.cs.txt').read_text().replace('output/ares/interior-v1','output/ares/observation-sign-v1')
(Path(__file__).parent/'baseline.cs.txt').write_text(capture)
views=[dict(name='detail',eye=[125,300,412],target=[0,600,426],fov=57),dict(name='context',eye=[300,70,280],target=[0,600,410],fov=70)]
(OUT/'capture-config.json').write_text(json.dumps(dict(views=views,variants=['before']),indent=2))
