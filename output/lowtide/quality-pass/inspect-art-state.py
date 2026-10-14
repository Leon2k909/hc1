import json
from pathlib import Path

scene=json.loads(Path('Assets/scenes/maps/Lowtide/lowtide.scene').read_text())
types=('Light','Fog','Exposure','Grade','Sky','Ambient','Bloom','Tone','Weather')
def walk(node):
    if isinstance(node,dict):
        if '__type' in node and any(t in node['__type'] for t in types):
            print(json.dumps(node))
        for value in node.values():
            walk(value)
    elif isinstance(node,list):
        for value in node:walk(value)
walk(scene)
