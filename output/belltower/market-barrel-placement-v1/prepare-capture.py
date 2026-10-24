import hashlib
import json
import math
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[3]
folder = Path(__file__).resolve().parent
phase = sys.argv[1]
assert phase in ('before', 'after')
helper = (root/'Sources/Belltower/editor/capture-preview-consistent.cs.txt').read_text()
helper = helper.replace('output/belltower/quality/consistent-preview.json',
                        'output/belltower/market-barrel-placement-v1/capture-request.json')
helper = helper.replace('Sources/Belltower/editor/capture-preview-consistent.cs.txt',
                        'output/belltower/market-barrel-placement-v1/capture.cs.txt')
(folder/'capture.cs.txt').write_text(helper)
position = (1370, 2045, 180) if phase == 'after' else (1195, 1995, 205)
target = (1450, 1845, 24) if phase == 'after' else (1355, 1785, 20)
delta = [b-a for a, b in zip(position, target)]
angles = (-math.degrees(math.atan2(delta[2], math.hypot(*delta[:2]))), math.degrees(math.atan2(delta[1], delta[0])), 0)
scene = root/'Assets/scenes/maps/Belltower/belltower.scene'
config = {'directory': 'market-barrel-placement-v1-'+phase+'-final', 'name': 'street', 'position': ','.join(map(str, position)),
          'angles': ','.join(map(str, angles)), 'fov': 80, 'width': 1600, 'height': 1000, 'exposure': 1.,
          'settle_ms': 0, 'expected_scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest()}
(folder/'capture-request.json').write_text(json.dumps(config, indent=2)+'\n')
print(json.dumps(config))
