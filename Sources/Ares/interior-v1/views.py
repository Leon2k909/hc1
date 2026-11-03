import json,sys
import native
views=[
 dict(name='overview',eye=[800,-680,274],target=[-200,640,330],fov=92),
 dict(name='floor',eye=[600,-450,64],target=[-300,300,270],fov=88),
 dict(name='wall',eye=[600,460,280],target=[1080,-260,470],fov=90),
 dict(name='pump',eye=[380,-430,72],target=[270,-270,65],fov=70)]
variants=['before','after']
if '--installed' in sys.argv:variants=['installed']
if '--baseline' in sys.argv:variants=['before']
(native.OUT/'capture-config.json').write_text(json.dumps(dict(views=views,variants=variants),indent=2)+'\n')
