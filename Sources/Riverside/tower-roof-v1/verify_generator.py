from pathlib import Path
import sys,ast,json,collections
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/tower-roof-v1';sys.path.insert(0,str(ROOT/'Tools'))
import riverside_parts as P,riverside_map as R,map_kit as K
t=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='guard_tower');env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'old-tower','exec'),env)
P.reset();a=K.Model();head_a=env['guard_tower'](a,*R.TOWER,aim=R.SEARCH_TARGET,ladder_model=True)
P.reset();b=K.Model();head_b=P.guard_tower(b,*R.TOWER,aim=R.SEARCH_TARGET,ladder_model=True,roof_model=True)
def faces(m):return collections.Counter((p,tuple(tuple(round(float(x),6) for x in v) for v in pts)) for p,polys in m.polygons.items() for pts,n in polys)
fa,fb=faces(a),faces(b);assert not fb-fa;assert sum((len(pts)-2)*c for (p,pts),c in (fa-fb).items())==4
assert str(a.boxes)==str(b.boxes) and str(a.hulls)==str(b.hulls) and list(head_a)==list(head_b)
assert len(P.TOWER_ROOFS)==1 and len(R.tower_roof_objects())==1
r=dict(OnlyOriginalRoofRemoved=True,CollisionPreserved=True,SearchlightPreserved=True,Position=K.to_world(P.TOWER_ROOFS[0][1]).tolist())
(OUT/'generator-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
