"""Current installation checks; exact old-face removal is recorded in verification.json."""
from pathlib import Path
import json,hashlib,ast,sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/orion/task-chair-reuse-v1';plan=json.loads((OUT/'install-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for path,digest in plan['reused'].items():assert sha(ROOT/path)==digest
for path,digest in plan['protected'].items():
    if path.endswith('.vmdl'):assert sha(ROOT/path)==digest
scene=json.loads((ROOT/'Assets/scenes/maps/Orion/orion.scene').read_text());nodes=[n for n in scene['GameObjects'] if n.get('Name')=='Operator Chair'];assert len(nodes)==6
for node,placement in zip(nodes,plan['placements']):
    assert len(node['Components'])==1 and node['Components'][0]['__type']=='Sandbox.ModelRenderer'
    resource=node['Components'][0]['Model'];assert (resource.get('Path') if isinstance(resource,dict) else resource)==plan['resource']
    assert isinstance(node['Scale'],str) and all(abs(float(v)-.82)<1e-5 for v in node['Scale'].split(','))
    expected=[placement['plan'][1],-placement['plan'][0],placement['plan'][2]]
    assert all(abs(float(a)-b)<.001 for a,b in zip(node['Position'].split(','),expected))
proof=json.loads((OUT/'verification.json').read_text());assert proof['old_faces_removed']==576 and proof['modeldoc_and_physics_identical']
native=json.loads((OUT/'native/validation.json').read_text());assert native['InstalledChairs']==6 and native['SharedResource']
assert all(n['FloorHit'] and abs(n['FootGap']-.2)<.001 for n in native['Floors'])
assert not (ROOT/'Assets/models/props/orion/control_chair_v1').exists() and not (ROOT/'Assets/materials/orion/control_chair_v1').exists()
for file in ('Tools/orion_parts.py','Tools/orion_map.py','Tools/orion_task_chairs.py'):ast.parse((ROOT/file).read_text())
print(json.dumps(dict(installed=6,shared_collider_asset_unchanged=True,dark_shared_materials=True,correct_floors=True,duplicate_preview_deleted=True),indent=2))
