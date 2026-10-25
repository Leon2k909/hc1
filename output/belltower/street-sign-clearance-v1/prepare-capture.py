from pathlib import Path
import hashlib
import json
import math
import sys

root=Path(__file__).resolve().parents[3]
directory=root/'output/belltower/street-sign-clearance-v1'
phase,view=sys.argv[1:]
assert phase in ('before','after') and view in ('west','east','west-oblique')
text=(root/'Sources/Belltower/editor/capture-fountain-water-v3.cs.txt').read_text()
text=text.replace('output/belltower/fountain-water-v3/capture-request.json',
                  'output/belltower/street-sign-clearance-v1/capture-request.json')
text=text.replace('Sources/Belltower/editor/capture-fountain-water-v3.cs.txt',
                  'output/belltower/street-sign-clearance-v1/capture.cs.txt')
helper=directory/'capture.cs.txt'
if helper.exists(): assert helper.read_text()==text
else: helper.write_text(text)
sign=-1 if view=='east' else 1
position=(414 if view=='west-oblique' else 376,sign*1935,150)
target=(376,sign*1851,127)
d=[b-a for a,b in zip(position,target)]
angles=(-math.degrees(math.atan2(d[2],math.hypot(*d[:2]))),math.degrees(math.atan2(d[1],d[0])),0)
request={'directory':'street-sign-clearance-v1-'+phase,'name':view,
         'width':1600,'height':1200,'fov':40,'exposure':1.,'settle_ms':0,
         'position':','.join(map(str,position)),'angles':','.join(map(str,angles)),
         'expected_scene_sha256':hashlib.sha256((root/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest()}
(directory/'capture-request.json').write_text(json.dumps(request,indent=2)+'\n')
print(json.dumps(request))
