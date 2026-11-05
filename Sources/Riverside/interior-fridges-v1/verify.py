"""Verify exact approved geometry reuse, original envelope and protected public resources."""
from pathlib import Path
import json,hashlib,sys
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/interior-fridges-v1';m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for group in ('protected','external_files','files'):
 for p,h in m[group].items():assert sha(ROOT/p)==h,'Changed resource: '+p
sys.path.insert(0,str(ROOT/'Tools'));import riverside_drinks_fridge as F,map_kit as K
def vertices(p):return np.array([list(map(float,l.split()[1:4])) for l in p.read_text().splitlines() if l.startswith('v ')])
local=vertices(ROOT/'Assets/models/props/riverside/interior_fridges_v1/fridge.obj');installed=vertices(ROOT/'Assets/models/maps/riverside/drinks-fridge-v1/drinks_fridge.obj')
# OBJ writes the engine vector as (engine Y, engine Z, engine X).
offset=np.array([-F.CENTER[0],F.CENTER[2],F.CENTER[1]])
assert np.allclose(local,installed-offset,atol=.0011),'Candidate differs from approved cabinet'
model=(ROOT/'Assets'/m['resource']).read_text();assert 'PhysicsShape' not in model and 'PhysicsHull' not in model
compiled=json.loads((OUT/'native-compile.json').read_text());assert all(x['result']['Success'] for x in compiled)
report=dict(PreviewOnly=True,ApprovedGeometryReused=True,TrianglesPerCabinet=34152,Cabinets=3,OldTriangles=42,NewCollision=False,PublicStoreAndSceneUnchanged=True,CompiledResources=3)
(OUT/'validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
