from pathlib import Path
from collections import Counter
import json
import math

root=Path(__file__).resolve().parents[3]
folder=Path(__file__).resolve().parent
before=json.loads((folder/'railhead-before.scene').read_text(encoding='utf-8'))
after=json.loads((root/'Assets/scenes/maps/Railhead/railhead.scene').read_text(encoding='utf-8'))

def flatten(objects):
    result={}
    for node in objects:
        result[node['__guid']]=node
        result.update(flatten(node.get('Children',[])))
    return result

def normalized(value):
    if isinstance(value,dict):
        if set(value)=={'Id','Path'}: return value['Path']
        return {k:normalized(v) for k,v in value.items()}
    if isinstance(value,list): return [normalized(v) for v in value]
    if isinstance(value,str) and ',' in value:
        try: return tuple(round(float(v),5) for v in value.split(','))
        except ValueError: pass
    return value


def equal(a,b):
    a,b=normalized(a),normalized(b)
    if isinstance(a,(int,float)) and isinstance(b,(int,float)):
        return math.isclose(a,b,rel_tol=1e-7,abs_tol=.001)
    if isinstance(a,(list,tuple)) and isinstance(b,(list,tuple)):
        return len(a)==len(b) and all(equal(x,y) for x,y in zip(a,b))
    if isinstance(a,dict) and isinstance(b,dict):
        return a.keys()==b.keys() and all(equal(a[k],b[k]) for k in a)
    return a==b

old,new=flatten(before['GameObjects']),flatten(after['GameObjects'])
missing=[old[k].get('Name',k) for k in old.keys()-new.keys()]
added=[new[k].get('Name',k) for k in new.keys()-old.keys()]
changes=[]
for key in old.keys()&new.keys():
    a,b=old[key],new[key]
    name=a.get('Name',key)
    for field in a.keys()&b.keys()-{'Components','Children','__version','Flags'}:
        if field=='__PrefabIdToInstanceId':
            assert all(b[field].get(k)==v for k,v in a[field].items()), 'Existing prefab identity changed'
            continue
        if not equal(a[field],b[field]):
            changes.append({'object':name,'field':field,'before':a[field],'after':b[field]})
    ac={c['__guid']:c for c in a.get('Components',[])}
    bc={c['__guid']:c for c in b.get('Components',[])}
    for component in ac.keys()-bc.keys():
        changes.append({'object':name,'removed_component':ac[component]['__type']})
    for component in bc.keys()-ac.keys():
        changes.append({'object':name,'added_component':bc[component]['__type']})
    for component in ac.keys()&bc.keys():
        ca,cb=ac[component],bc[component]
        for field in ca.keys()&cb.keys()-{'__version','Flags'}:
            if not equal(ca[field],cb[field]):
                changes.append({'object':name,'component':ca['__type'],'field':field,'before':ca[field],'after':cb[field]})
        if ca['__type'].endswith(('Collider','SpawnPoint','BombSite','MapLocation','ObjectiveSpot')):
            meaningful={k:v for k,v in cb.items() if k not in ca and v not in (None,False,0,'','0,0,0') and not k.startswith('__')}
            if meaningful: changes.append({'object':name,'component':ca['__type'],'added_values':meaningful})

report={'before_objects':len(old),'after_objects':len(new),'missing_objects':missing,'added_objects':sorted(added),
        'changes':changes,'change_fields':dict(Counter((c.get('component','Object')+'.'+c.get('field','structure')) for c in changes))}
(folder/'scene-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='changes'},indent=2))
print('Non-lighting changes:')
unexpected=[]
for c in changes:
    if c.get('component') not in {'Sandbox.DirectionalLight','Sandbox.PointLight','Sandbox.AmbientOcclusion','Sandbox.ColorGrading','Sandbox.Vignette','Sandbox.Tonemapping'}:
        print(json.dumps(c))
        unexpected.append(c)
assert not missing,'Original scene objects were removed'
assert not unexpected,'Non-lighting changes need review'
assert len(added)==6 and set(added)=={'Hall Kiosk East 1','Hall Kiosk East 2','Hall Kiosk West 1','Hall Kiosk West 2','Ironwork Details','Station Indirect Light'}
for key,value in before['SceneProperties'].items():
    if key=='Metadata':
        assert all(equal(v,after['SceneProperties'][key][k]) for k,v in value.items()), 'Scene metadata changed'
    else:
        assert equal(value,after['SceneProperties'][key]), f'Scene setting changed: {key}'
print('All existing objects, transforms, collision properties and gameplay components retained. Only six intended objects added.')
