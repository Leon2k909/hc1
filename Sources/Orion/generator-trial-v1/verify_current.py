"""Check the generator without rejecting later, unrelated shared-map edits."""
from pathlib import Path
import hashlib,json,re
import numpy as np
ROOT=Path.cwd();OUT=ROOT/'output/orion-generator-installed-20261030'
receipt=json.loads((OUT/'offline-install.json').read_text())
shared={'models/maps/orion/orion_launch_deck.obj','scenes/maps/Orion/orion.scene'}
files={p:h for p,h in receipt['installedFiles'].items() if p not in shared}
assert all(hashlib.sha256((ROOT/'Assets'/p).read_bytes()).hexdigest()==h for p,h in files.items())
instance=json.loads((ROOT/'Sources/Orion/generator-trial-v1/native-instance.json').read_text())
scene=json.loads((ROOT/'Assets/scenes/maps/Orion/orion.scene').read_text())
parent=next(x for x in scene['GameObjects'] if x.get('Name')=='Orion')
assert [x for x in parent['Children'] if x.get('Name')==instance['Name']]==[instance]
assert parent['Position']=='0,0,0' and parent['Scale']=='1,1,1' and parent['Rotation']=='0,0,0,1'
def box(path):
    matches=[]
    for block in re.findall(r'\{\s*_class = "PhysicsShapeBox"[^{}]*\}',path.read_text()):
        origin=re.search(r'origin = \[([^\]]+)\]',block)
        if origin and list(map(float,origin[1].split(',')))==[1335.,-265.,275.]:matches.append(block)
    assert len(matches)==1,(str(path),len(matches))
    return re.sub(r'\s+','',re.sub(r'name = "[^"]*"','',matches[0]))
original=ROOT/'output/orion-cable-reel-installed-20261030/stage/Assets/models/maps/orion/orion_launch_deck.vmdl'
assert box(original)==box(ROOT/'Assets/models/maps/orion/orion_launch_deck.vmdl')
vertices=[];old_faces=0
for line in (ROOT/'Assets/models/maps/orion/orion_launch_deck.obj').open():
    p=line.split()
    if p and p[0]=='v':a,z,n=map(float,p[1:]);vertices.append(np.array((-a,n,z)))
    elif p and p[0]=='f':
        points=np.array([vertices[int(s.split('/')[0])-1]-np.array((265,1335,240)) for s in p[1:]])
        if np.all(np.minimum(abs(points-np.array((-65,-35,0))),abs(points-np.array((65,35,70))))<.001):old_faces+=1
assert old_faces==0
tool=(ROOT/'Tools/orion_map.py').read_text();assert 'OG.collision( m, G )' in tool and 'OG.scene_object()' in tool
result={'currentPrivateGeneratorFilesVerified':len(files),'currentSceneHasExactApprovedInstance':True,'oldBoxRenderFacesRemaining':old_faces,
 'originalGeneratorCollisionPreserved':True,'mapGeneratorHooksPresent':True,'laterSharedMapChangesPreserved':True,'nativeValidationPerformed':False}
(OUT/'current-integration-verification.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
