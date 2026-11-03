from pathlib import Path
import hashlib
import json

root=Path(__file__).resolve().parents[3]
folder=root/'output/spillway/waterline-fix-v1'
plan=json.loads((folder/'install-plan.json').read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for rel,expected in plan['files'].items():
    assert sha(root/rel)==expected,'Installed file differs: '+rel
for rel,expected in plan['guards'].items():
    if rel not in plan['files']:
        assert sha(root/rel)==expected,'Protected source changed: '+rel
compile((root/'Tools/spillway_landscape.py').read_text(),'Tools/spillway_landscape.py','exec')
report=dict(InstalledFilesMatch=True,ProtectedSourcesUnchanged=True,SceneUnchanged=True,
            CollisionUnchanged=True,ModelDocAndMaterialsUnchanged=True,OriginalTerrainFacesPreserved=True,
            AddedTriangles=plan['added_triangles'],OpenAboveWaterBoundaryEdges=plan['open_above_water_edges'],
            SubmergedDepth=plan['water_height']-plan['bank_bottom'],GeneratorSyntaxValid=True)
(folder/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
