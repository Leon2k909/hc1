"""Prepare the existing native capture method with task-local destinations."""
from pathlib import Path
import argparse
import hashlib
import json
import math

ROOT=Path(__file__).resolve().parents[1]
FOLDER=ROOT/'output/belltower/barrels-v2'
parser=argparse.ArgumentParser();parser.add_argument('name');parser.add_argument('--east',action='store_true');parser.add_argument('--detail',action='store_true');args=parser.parse_args()
helper=ROOT/'Sources/Belltower/editor/capture-clock-barrels-v2.cs.txt'
original=(ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt').read_text()
text=original.replace('output/belltower/fountain-ornaments-v2/capture-request.json','output/belltower/barrels-v2/capture-request.json')
text=text.replace('output/belltower/quality','output/belltower/barrels-v2/captures')
text=text.replace('Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt','Sources/Belltower/editor/capture-clock-barrels-v2.cs.txt')
assert text!=original
previous=text
text=text.replace('if (session.HasUnsavedChanges) throw new InvalidOperationException("This diagnostic requires the saved Belltower document.");','var wasDirty = session.HasUnsavedChanges;')
text=text.replace('|| session.HasUnsavedChanges ||','|| session.HasUnsavedChanges != wasDirty ||')
text=text.replace('&& !session.HasUnsavedChanges &&','&& session.HasUnsavedChanges == wasDirty &&')
if helper.exists():assert helper.read_text() in (previous,text),'Shared capture helper changed; review before replacing.'
helper.write_text(text)
position=(1190,490,65) if args.detail else (1260,540,112)
target=(1120,404,22) if args.detail else (1105,335,54)
if args.east:position=(position[0],-position[1],position[2]);target=(target[0],-target[1],target[2])
delta=[b-a for a,b in zip(position,target)]
pitch=-math.degrees(math.atan2(delta[2],math.hypot(delta[0],delta[1])))
yaw=math.degrees(math.atan2(delta[1],delta[0]))
sha=hashlib.sha256((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest()
config={'directory':'native','name':args.name,'position':','.join(map(str,position)),
        'angles':f'{pitch},{yaw},0','width':1600,'height':1000,'fov':55 if args.detail else 66,
        'exposure':1.0,'settle_ms':0,'expected_scene_sha256':sha}
(FOLDER/'capture-request.json').write_text(json.dumps(config,indent=2)+'\n')
print(json.dumps(config))
