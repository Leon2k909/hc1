from pathlib import Path
import sys,ast,json,collections
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/still-here-board-v1';sys.path.insert(0,str(ROOT/'Tools'))
import riverside_parts as P,riverside_map as R,map_kit as K
t=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in t.body if isinstance(n,ast.FunctionDef) and n.name=='park_sign');env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'old-sign','exec'),env)
P.reset();a=K.Model();env['park_sign'](a,*R.SIGN,scale=.7,height=370);lights=list(P.LIGHTS)
P.reset();b=K.Model();P.park_sign(b,*R.SIGN,scale=.7,height=370,board_model=True)
def faces(m):return collections.Counter((p,tuple(tuple(round(float(x),6) for x in v) for v in pts)) for p,polys in m.polygons.items() for pts,n in polys)
fa,fb=faces(a),faces(b);assert not fb-fa;assert sum((len(pts)-2)*c for (p,pts),c in (fa-fb).items())==14
assert str(a.boxes)==str(b.boxes) and str(a.hulls)==str(b.hulls) and lights==P.LIGHTS
r=dict(OnlyOriginalBoardRemoved=True,CollisionPreserved=True,PointLightsPreserved=True,MainSignAndPostsPreserved=True,Position=K.to_world(P.GRAFFITI_BOARDS[0][1]).tolist())
(OUT/'generator-check.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
