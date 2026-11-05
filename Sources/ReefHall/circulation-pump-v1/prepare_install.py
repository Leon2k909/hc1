"""Stage the approved filter pump without rebuilding the room or its collision."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/reefhall/circulation-pump-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
validation=json.loads((OUT/'validation.json').read_text());assert validation['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h];assert not changed,changed
public=ROOT/'Assets/models/maps/reefhall/reefhall_filter.vmdl';source=ROOT/manifest['source'];original=public.read_text()
assert 'installed_circulation_pump.obj' not in original,'Already installed; inspect receipt'
before=OUT/'install-before';stage=OUT/'install-stage';dest=stage/'Assets/models/maps/reefhall/circulation-pump-v1';dest.mkdir(parents=True,exist_ok=True)
generator=ROOT/'Tools/reefhall_map.py'
for path in (public,source,generator):
 backup=before/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
candidate=ROOT/'Assets/models/maps/reefhall/circulation-pump-v1/circulation_pump.obj'
obj=candidate.read_text().replace('mtllib circulation_pump.mtl','mtllib installed_circulation_pump.mtl')
obj=re.sub(r'(?m)^usemtl (.+)$',lambda m:'usemtl rh_cp_'+m[1],obj);(dest/'installed_circulation_pump.obj').write_text(obj)
mtl=re.sub(r'(?m)^newmtl (.+)$',lambda m:'newmtl rh_cp_'+m[1],candidate.with_suffix('.mtl').read_text());(dest/'installed_circulation_pump.mtl').write_text(mtl)
base=(candidate.parent/'filter_without_pump.obj').read_text().replace('mtllib filter_without_pump.mtl','mtllib '+source.with_suffix('.mtl').name)
target=stage/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(base)
own=candidate.with_suffix('.vmdl').read_text();pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group().replace('circulation_pump.obj','installed_circulation_pump.obj')
oldnode=re.search(pattern,original,re.S).group();merged=original.replace(oldnode,oldnode+'\n'+node,1)
remaps=[r.replace('from = "','from = "rh_cp_') for r in re.findall(r'\{ from = "[^\n]+?\}',own)]
assert not set(re.findall(r'from = "([^"]+)"','\n'.join(remaps)))&set(re.findall(r'from = "([^"]+)"',original))
index=merged.index('\t'*7+'{ from = ');merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(before={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (public,source)},files=files,new_triangles=manifest['triangles'],old_triangles=manifest['original_triangles']),indent=2))
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();X,Y,Z='):build.index('legacy=K.Model();')];body=body[:body.index(';count=K.write_model')]
helper='''"""Approved ReefHall circulation pump, exact prototype geometry and texture mapping."""
import math
import numpy as np
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
import railhead_dress_detail as D
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    # Bake the prototype's projected and grain UVs before joining the room.
    offset=K.uv_offset('circulation_pump')
    for paint,faces in m.polygons.items():
        for i,(points,normal) in enumerate(faces):
            if (paint,i) in m.polygon_uvs:continue
            world=[K.to_world(p) for p in points];wn=K.to_world(normal);tile=m.tile_overrides[paint]
            coords=[K.face_uv(p,wn,paint,offset,tile) for p in world]
            if paint in m.grain_paints:
                edges=[world[(j+1)%len(world)]-p for j,p in enumerate(world)]
                along=K.normalise(max(edges,key=lambda e:np.linalg.norm(e)));across=np.cross(wn,along)
                coords=[(float(np.dot(p,across)/tile+offset[0]),float(np.dot(p,along)/tile+offset[1])) for p in world]
            m.polygon_uvs[(paint,i)]=coords
    return m

def append_to(target):
    # The original plinth and cover boxes, with no legacy render faces.
    fr=R.Frame((-380,1610),(1,0))
    R.fbox(target,fr,-34,34,-18,18,0,8,None,R.METAL)
    R.fbox(target,fr,-34,40,-21,21,8,48,None,R.METAL)
    m=model()
    for paint,faces in m.polygons.items():
        alias='rh_cp_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs[(paint,i)],normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/reefhall_circulation_pump.py').write_text(helper)
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import reefhall_circulation_pump as F
proof=OUT/'approved-generator.obj';K.write_obj(proof,F.model(),'circulation_pump');assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:]
assert not F.model().boxes and not F.model().hulls
g=generator.read_text();old='''    """ A circulation pump on a plinth: a blue motor, the volute and its pipe stubs. """''';assert g.count(old)==1
g=g.replace(old,old+'''
    if tuple(centre[:2]) == (-380,1610) and abs(yaw % 360.0) < 1e-8:
        from reefhall_circulation_pump import append_to as append_approved_pump
        append_approved_pump(model)
        return''');generator.write_text(g)
script=(ROOT/'Sources/Railhead/brick-pallet-v1/install.cs.txt').read_text().replace('output/railhead/brick-pallet-v1','output/reefhall/circulation-pump-v1').replace('Assets/models/maps/railhead/','Assets/models/maps/reefhall/').replace('InstalledPallets','InstalledPumps');(HERE/'install.cs.txt').write_text(script)
verify=(ROOT/'Sources/Railhead/brick-pallet-v1/verify_installed.py').read_text()
for old,new in [('models/maps/railhead/railhead_dress_east.vmdl','models/maps/reefhall/reefhall_filter.vmdl'),('Assets/models/maps/railhead/cable-drum-v1/east_without_drum.obj','Assets/models/maps/reefhall/reefhall_filter.obj'),('Assets/models/maps/railhead/railhead_dress_east.vmdl','Assets/models/maps/reefhall/reefhall_filter.vmdl'),('Tools/railhead_map.py','Tools/reefhall_map.py'),('Assets/models/maps/railhead/brick-pallet-v1/installed_brick_pallet.obj','Assets/models/maps/reefhall/circulation-pump-v1/installed_circulation_pump.obj'),('==266','==220'),('==24992','==16196'),('pallets=1,bricks=520','pumps=1'),('old_render_triangles_removed=266,new_triangles=24992','old_render_triangles_removed=220,new_triangles=16196')]:verify=verify.replace(old,new)
(HERE/'verify_installed.py').write_text(verify)
print(json.dumps(dict(pumps=1,staged_files=len(files),old_triangles=220,new_triangles=16196,generator_matches_approved=True)))
