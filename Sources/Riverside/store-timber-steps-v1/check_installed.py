from pathlib import Path
import sys,json,ast,collections
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OUT=ROOT/'output/riverside/store-timber-steps-v1'
sys.path.insert(0,str(ROOT/'Tools'));import riverside_parts as P,riverside_map as R,map_kit as K
t=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='steps');env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'old-steps','exec'),env)
P.reset();a=K.Model();env['steps'](a,(235,490),(0,1),90,19.5,'rs_wood','wood',rise=7)
P.reset();b=K.Model();P.steps(b,(235,490),(0,1),90,19.5,'rs_wood','wood',rise=7,model=True)
assert sum(len(pts)-2 for polys in a.polygons.values() for pts,n in polys)==36 and not any(b.polygons.values())
assert str(a.boxes)==str(b.boxes) and str(a.hulls)==str(b.hulls) and len(R.store_step_objects())==1
(OUT/'generator-check.json').write_text(json.dumps(dict(OnlyOriginalStepsRemoved=True,CollisionPreserved=True),indent=2))
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'));from native import Editor
code=(HERE/'context.cs.txt').read_text().replace('output/riverside/store-timber-steps-v1/context','output/riverside/store-timber-steps-v1/installed').replace('store_timber_steps_v1/legacy_steps.vmdl','store_timber_steps_v1/steps.vmdl')
a=code.index('        var low=');b=code.index('        oldObject = ',a)
code=code[:a]+'        newObject=scene.GetAllObjects(false).Single(g=>g.Name=="Lucky Stop Timber Steps");\n'+code[b:]
code=code.replace('new[] { "before", "after" }','new[] { "after" }')
with Editor() as e:
 r=e.script(code,'check-installed-store-steps.cs');(OUT/'installed-capture.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2));assert r['SourceUnchanged'] and not r['ErrorModels']
