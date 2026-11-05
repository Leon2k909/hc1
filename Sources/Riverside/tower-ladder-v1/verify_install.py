from pathlib import Path
import sys,json,ast,collections,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/tower-ladder-v1';sys.path.insert(0,str(ROOT/'Tools'))
import riverside_parts as P
import riverside_map as R
import map_kit as K
tree=ast.parse((OUT/'install-before/riverside_parts.py').read_text());fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='guard_tower');env=dict(P.__dict__);exec(compile(ast.Module(body=[fn],type_ignores=[]),'old-guard-tower','exec'),env)
P.reset();a=K.Model();head0=env['guard_tower'](a,R.TOWER[0],R.TOWER[1],aim=R.SEARCH_TARGET)
P.reset();b=K.Model();head1=P.guard_tower(b,R.TOWER[0],R.TOWER[1],aim=R.SEARCH_TARGET,ladder_model=True)
def faces(m):return collections.Counter((paint,tuple(tuple(round(float(v),6) for v in p) for p in pts)) for paint,polys in m.polygons.items() for pts,n in polys)
fa,fb=faces(a),faces(b);assert not fb-fa
removed=fa-fb;assert sum((len(pts)-2)*c for (paint,pts),c in removed.items())==450
assert str(a.boxes)==str(b.boxes) and str(a.hulls)==str(b.hulls) and list(head0)==list(head1)
p=json.loads((OUT/'install-plan.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/p['source'])==p['source_after'] and sha(ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl')==p['dressing_vmdl_before']
before=json.loads((OUT/'install-before/riverside.scene').read_text());after=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text())
group=next(g for g in after['GameObjects'] if g.get('Name')=='Guard Tower Ladders');assert len(group['Children'])==1
item=group['Children'][0];assert item['Name']=='Guard Tower Ladder' and len(item['Components'])==1
ids={g['__guid'] for g in before['GameObjects']};trimmed=dict(after);trimmed['GameObjects']=[g for g in after['GameObjects'] if g['__guid'] in ids];assert trimmed==before,'Concurrent scene edit requires inspection'
assert (ROOT/'Assets/models/props/riverside/tower_ladder_v1/legacy_ladder.vmdl').exists()
assert (ROOT/'Assets/models/props/riverside/tower_ladder_v1/legacy_ladder_steel.vmdl').exists()
r=dict(Installed=True,RemovedOldMapTriangles=450,OriginalLadderAssetPreserved=True,SeparateSteelFinish=True,CollisionPreserved=True,SearchlightAndTowerPreserved=True,ExistingSceneObjectsPreserved=True,PublicModelDocPreserved=True,GeneratorVerified=True)
(OUT/'installed.json').write_text(json.dumps(r,indent=2));print(json.dumps(r,indent=2))
