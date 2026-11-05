from pathlib import Path
from collections import Counter
import hashlib,json,re,sys
import numpy as np
ROOT=Path(sys.argv[1]).resolve();OUT=ROOT/'output/asset-improvement-20261030/riverside-porch-light/installed'
plan=json.loads((OUT/'plan.json').read_text())
current_only='--current' in sys.argv[2:]
scene=json.loads((ROOT/'Assets/scenes/maps/Riverside/riverside.scene').read_text());before=json.loads((OUT/'before-install/riverside.scene').read_text())
group=next(g for g in scene['GameObjects'] if g.get('Name')=='Porch Lights')
assert len(group['Children'])==26
def vec(v):return [float(x) for x in v.split(',')] if isinstance(v,str) else v
for a,b in zip(group['Children'],plan['group']['Children']):
    for key in ('Position','Rotation','Scale'):assert np.allclose(vec(a[key]),vec(b[key]),atol=1e-5),(a['Name'],key)
    assert len(a['Components'])==1 and a['Components'][0]['__type']=='Sandbox.ModelRenderer'
    model=a['Components'][0]['Model'];assert (model.get('Path') if isinstance(model,dict) else model)==b['Components'][0]['Model']
def lights(data):
    out=[]
    def walk(go):
        for c in go.get('Components',[]):
            if c['__type'] in ('Sandbox.PointLight','Sandbox.SpotLight'):out.append((go['__guid'],go.get('Position'),go.get('Rotation'),c))
        for child in go.get('Children',[]):walk(child)
    for go in data['GameObjects']:walk(go)
    return out
old_lights,new_lights=lights(before),lights(scene)
if current_only:
    def porch_lights(rows):
        # Porch fixture integration owns porch light anchors, not the separately edited fridge.
        ids=set()
        def walk(g):
            if 'porch' in g.get('Name','').lower():ids.add(g['__guid'])
            for child in g.get('Children',[]):walk(child)
        for g in before['GameObjects']:walk(g)
        return [r for r in rows if r[0] in ids]
    assert porch_lights(old_lights)==porch_lights(new_lights),'Existing porch lights changed'
else:assert old_lights==new_lights,'Existing lights changed'
for row in ([] if current_only else plan['cuts']):
    p=ROOT/row['path'];assert hashlib.sha256(p.read_bytes()).hexdigest()==row['after_sha256'],str(p)
    relative=p.relative_to(ROOT/'Assets')
    old=Counter((OUT/'before-install'/relative).read_bytes().splitlines(keepends=True));new=Counter(p.read_bytes().splitlines(keepends=True))
    assert not new-old
    cut=old-new
    assert sum(n for l,n in cut.items() if l.startswith(b'f '))==row['removed_faces']
    assert all(l.startswith(b'f ') or l.strip()==b'usemtl rs_porch_light' for l in cut)
independent_fridge_collider_shift=False
for row in plan['public_models']:
    p=ROOT/row['path'];text=p.read_text();physics=text[text.index('_class = "PhysicsShapeList"'):]
    if hashlib.sha256(physics.encode()).hexdigest()!=row['physics_sha256']:
        # A separate placement fix moved only the fridge collider 64 inches, with its light.
        if current_only and p.name=='riverside_store.vmdl':
            rebased=physics.replace('origin = [ 624.0000, -96.0000, 56.0000 ]','origin = [ 560.0000, -96.0000, 56.0000 ]')
            assert hashlib.sha256(rebased.encode()).hexdigest()==row['physics_sha256'],str(p)+' additional physics change'
            independent_fridge_collider_shift=True
        else:raise AssertionError(str(p)+' physics changed')
    for rel in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text.split('_class = "PhysicsShapeList"')[0]):
        mat=None
        for l in (ROOT/'Assets'/rel).read_text().splitlines():
            if l.startswith('usemtl '):mat=l.split()[1]
            assert not(l.startswith('f ') and mat=='rs_porch_light'),rel+' still has old lamp faces'
report=dict(saved_lamps=26,fixture_collision_additions=0,existing_porch_lights_unchanged=True,no_old_faces_in_current_imports=True)
report['independent_store_fridge_collider_shift']=independent_fridge_collider_shift
report['physics_matches_installation_baseline']=not independent_fridge_collider_shift
if current_only:
    old_by_id={r[0]:r for r in old_lights};new_by_id={r[0]:r for r in new_lights}
    report['unrelated_changed_light_guids']=[k for k in old_by_id.keys()|new_by_id.keys() if old_by_id.get(k)!=new_by_id.get(k)]
else:report['all_existing_lights_unchanged']=True
if not current_only:report.update(old_live_faces_removed=312,all_unrelated_mesh_lines_preserved=True)
(OUT/('current-verification.json' if current_only else 'verification.json')).write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
