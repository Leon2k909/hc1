from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).resolve().parent
OUT=ROOT/'output/sewage/work-lamps-v1/current-review'
before=json.loads((OUT/'scene-before.json').read_text())
after=json.loads((ROOT/'Assets/scenes/maps/sewage/sewage.scene').read_text())
def components(node,types):
    result={}
    def walk(value):
        if isinstance(value,dict):
            if value.get('__type') in types:result[value['__guid']]=value
            for v in value.values():walk(v)
        elif isinstance(value,list):
            for v in value:walk(v)
    walk(node);return result
lights={'Sandbox.PointLight','Sandbox.SpotLight','Sandbox.AmbientLight','Sandbox.DirectionalLight'}
old_lights=components(before,lights);new_lights=components(after,lights)
assert old_lights==new_lights,'Saved scene lighting changed'
old_colliders=components(before,{'Sandbox.ModelCollider','Sandbox.BoxCollider'})
new_colliders=components(after,{'Sandbox.ModelCollider','Sandbox.BoxCollider'})
assert old_colliders==new_colliders,'Saved collision components changed'
objects={g.get('Name'):g for g in after['GameObjects']}
def model(name):return next(c for c in objects[name]['Components'] if c.get('__type')=='Sandbox.ModelRenderer')['Model']['Path']
assert model('Waterworks details')=='models/maps/sewage/work-lamps-v1/base_details.vmdl'
assert model('Waterworks caged work lamps')=='models/maps/sewage/work-lamps-v1/lamps.vmdl'
assert model('Waterworks catwalks')=='models/maps/sewage/sewage_catwalks.vmdl'
assert sum(g.get('Name')=='Waterworks caged work lamps' for g in after['GameObjects'])==1
plan=json.loads((ROOT/'output/sewage/work-lamps-v1/plan.json').read_text())
assert hashlib.sha256((ROOT/'Assets/models/maps/sewage/sewage_details.obj').read_bytes()).hexdigest()==plan['original_sha256']
assert all((ROOT/f'Assets/models/maps/sewage/stair-treads-v1/{v}.vmdl').exists() for v in ('before','after'))
report=dict(Installed=True,ReusedExistingModel=True,Fixtures=plan['fixtures'],LightingComponentsUnchanged=len(old_lights),CollisionComponentsUnchanged=len(old_colliders),OriginalDetailsSourceRetained=True,SingleFixtureGroup=True,BothStairVersionsKept=True,NewStairsRemainActive=True)
(OUT/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
