"""Audit the native scene roundtrip and generator parity for grounded trees."""
import json,sys,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'Tools'))
import forestbase_map as M
STAGE=Path(__file__).resolve().parent
def nodes(scene):
    result={}
    def walk(items,parent=None):
        for node in items:
            result[node['__guid']]=({k:v for k,v in node.items() if k!='Children'},parent,[c['__guid'] for c in node.get('Children',[])])
            walk(node.get('Children',[]),node['__guid'])
    walk(scene['GameObjects'])
    return result
def model(node):
    value=next(c['Model'] for c in node['Components'] if c['__type']=='Sandbox.ModelRenderer')
    return value['Path'] if isinstance(value,dict) else value
def vec(s):return tuple(map(float,s.split(',')))
before=json.loads((STAGE/'canonical-before.json').read_text())
saved=json.loads((STAGE/'canonical-saved.json').read_text())
old,new=nodes(before),nodes(saved)
edits={r['id']:r for r in json.loads((STAGE/'accepted-tree-edits.json').read_text())}
assert old.keys()==new.keys()
assert {k:v for k,v in before.items() if k!='GameObjects'}=={k:v for k,v in saved.items() if k!='GameObjects'}
changed=[]
for guid,(a,parent,children) in old.items():
    b,p,c=new[guid]
    assert parent==p and children==c
    if a==b:continue
    assert guid in edits, a['Name']
    edit=edits[guid]
    assert max(abs(a-b) for a,b in zip(vec(b['Position']),edit['world']))<.002
    assert model(b)==edit['model']
    aa=json.loads(json.dumps(a));bb=json.loads(json.dumps(b))
    aa.pop('Position');bb.pop('Position')
    for n in (aa,bb):
        assert len(n['Components'])==1 and n['Components'][0]['__type']=='Sandbox.ModelRenderer'
        n['Components'][0].pop('Model')
    assert aa==bb, a['Name']
    changed.append(a['Name'])
assert len(changed)==16
M.build(visual_chunks=[])
saved_by_name={n['Name']:n for n,_,_ in new.values() if n.get('Name','').startswith(('Fir ','Young fir ','Forest middle ','Far fir ','Forest understory '))}
errors=[]
for name,path,pos,yaw,scale in M.INSTANCES:
    if name not in saved_by_name:continue
    n=saved_by_name[name]
    assert model(n)==path,(name,model(n),path)
    errors.append(max(abs(a-b) for a,b in zip(vec(n['Position']),M.K.to_world(pos))))
    assert max(abs(a-b) for a,b in zip(vec(n['Scale']),scale))<.001
assert len(errors)==525 and max(errors)<.02
report=dict(changedTrees=changed,treeCount=525,canonicalNodes=len(new),
            allOtherNativeSceneContentUnchanged=True,changedTreeColliders=0,
            generatorTrees=len(errors),maximumCoordinateErrorInches=max(errors),
            sourceSceneSha256=hashlib.sha256((ROOT/'Assets/scenes/maps/forestbase/forestbase.scene').read_bytes()).hexdigest(),
            scope='Engine-normalized before/after scene identity and generator parity. No FPS or multiplayer acceptance claim.')
(STAGE/'grounded-audit.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
