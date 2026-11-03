from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/ares/constructed-interior-v3'
config=dict(variants=[dict(name='review',lightGain=1.4,temperature=5000,bounce=1.8,contrast=.85,shadows=True,diffuseWork=True,trial=True)],
 views=[dict(name='overview',eye=[800,-680,274],target=[-200,640,330],fov=92),
        dict(name='hero',eye=[940,-640,280],target=[-70,300,330],fov=78),
        dict(name='floor',eye=[600,-450,64],target=[-300,300,270],fov=88),
        dict(name='pump',eye=[390,-410,86],target=[270,-270,38],fov=68)])
(OUT/'capture-config.json').write_text(json.dumps(config,indent=2))
