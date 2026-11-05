from pathlib import Path
import sys,json,ast,collections,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OUT=ROOT/'output/riverside/interior-fridges-v1'
sys.path.insert(0,str(ROOT/'Tools'));import riverside_parts as P,riverside_map as R,map_kit as K
t=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='fridge');env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'original-fridge','exec'),env)
positions=[(348,760+k*34,20) for k in range(3)]
P.reset();a=K.Model()
for e,n,z in positions:env['fridge'](a,(e,n),(-1,0),z)
lights=list(P.LIGHTS);P.reset();b=K.Model()
for e,n,z in positions:P.fridge(b,(e,n),(-1,0),z,model=True)
def faces(m):return collections.Counter((p,tuple(tuple(round(float(x),6) for x in v) for v in pts)) for p,polys in m.polygons.items() for pts,n in polys)
fa,fb=faces(a),faces(b);assert not fb-fa;assert sum((len(pts)-2)*c for (p,pts),c in (fa-fb).items())==42
assert str(a.boxes)==str(b.boxes) and str(a.hulls)==str(b.hulls) and lights==P.LIGHTS
assert len(P.INTERIOR_FRIDGES)==3 and len(R.interior_fridge_objects())==3 and all(i[2]==-90 for i in P.INTERIOR_FRIDGES)
(OUT/'generator-check.json').write_text(json.dumps(dict(OnlyOriginalFridgesRemoved=True,CollisionPreserved=True,PointLightsPreserved=True,Instances=3),indent=2))
before=json.loads((OUT/'install-before/riverside.scene').read_text());after=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text());ids={g['__guid'] for g in before['GameObjects']};trim=dict(after);trim['GameObjects']=[g for g in after['GameObjects'] if g['__guid'] in ids];assert trim==before
group=next(g for g in after['GameObjects'] if g.get('Name')=='Interior Drinks Fridges');assert len(group['Children'])==3
for k,item in enumerate(group['Children']):
 assert item['Name']==f'Interior Drinks Fridge {k+1}' and len(item['Components'])==1
 c=item['Components'][0];assert c['__type']=='Sandbox.ModelRenderer' and c['Model']['Path']=='models/props/riverside/interior_fridges_v1/fridge.vmdl'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'));from native import Editor
code=(HERE/'context.cs.txt').read_text().replace('output/riverside/interior-fridges-v1/context','output/riverside/interior-fridges-v1/installed').replace('interior_fridges_v1/legacy_fridge.vmdl','interior_fridges_v1/fridge.vmdl')
a=code.index('        var low=');b=code.index('        var holder =',a)
code=code[:a]+'''        newObjects=scene.GetAllObjects(false).Where(g=>g.Name.StartsWith("Interior Drinks Fridge ")).ToList();
        if(newObjects.Count!=3)throw new Exception("Saved fridge count differs");
'''+code[b:]
code=code.replace('new[] { "before", "after" }','new[] { "after" }')
with Editor() as e:
 r=e.script(code,'check-saved-interior-fridges.cs');(OUT/'installed-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));assert r['SourceUnchanged'] and not r['ErrorModels']
