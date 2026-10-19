from pathlib import Path
import json
import sys

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools'))
import railhead_map as R
import railhead_station as S
import railhead_ironwork as I

out=Path(__file__).resolve().parent/'reproduction'
out.mkdir(exist_ok=True)
models=S.build()
report={}
for name in ('railhead_east','railhead_west'):
    model=R.configure(models[name])
    R.K.write_model(out,'models/maps/railhead',name,model)
    generated=(out/(name+'.vmdl')).read_text(encoding='utf-8')
    current=(root/'Assets/models/maps/railhead'/(name+'.vmdl')).read_text(encoding='utf-8')
    marker='_class = "PhysicsShapeList"'
    assert generated.split(marker,1)[1]==current.split(marker,1)[1],name+' collision differs'
    generated_count=sum(line.startswith('f ') for line in (out/(name+'.obj')).open(encoding='utf-8'))
    current_count=sum(line.startswith('f ') for line in (root/'Assets/models/maps/railhead'/(name+'.obj')).open(encoding='utf-8'))
    report[name]={'generated_triangles':generated_count,'current_triangles':current_count,'physics_identical':True}
    assert generated_count==current_count,(name,generated_count,current_count)
iron=I.build()
assert not iron.boxes and not iron.hulls
report['ironwork']={'triangles':iron.triangle_count(),'collision_shapes':0}

def flatten(objects):
    for node in objects:
        yield node
        yield from flatten(node.get('Children',[]))
scene=json.loads((root/'Assets/scenes/maps/Railhead/railhead.scene').read_text(encoding='utf-8'))
nodes=list(flatten(scene['GameObjects']))
by_name={n['Name']:n for n in nodes if 'Name' in n}
for name,position,color,radius,shadows in R.lights():
    component=next(c for c in by_name[name]['Components'] if c['__type']=='Sandbox.PointLight')
    assert all(abs(float(a)-float(b))<1e-5 for a,b in zip(color.split(','),component['LightColor'].split(','))),name
    assert radius==component['Radius'] and shadows==component['Shadows'],name
    if R.is_fill_light(name): assert component['Contribution']=='Diffuse',name
report['point_lights_match']=len(R.lights())
(out/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report,indent=2))
