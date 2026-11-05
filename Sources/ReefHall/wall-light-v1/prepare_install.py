"""Stage the approved filter wall light without rebuilding the room or its collision."""
from pathlib import Path
import hashlib,json,re,sys
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/reefhall/wall-light-v1'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
validation=json.loads((OUT/'validation.json').read_text());assert validation['actual_play_mode_checked']
manifest=json.loads((OUT/'manifest.json').read_text());assert all(sha(ROOT/p)==h for p,h in manifest['files'].items())
guard=json.loads((OUT/'source-guard.json').read_text());changed=[p for p,h in guard.items() if sha(ROOT/p)!=h]
allowed={'Assets/models/maps/reefhall/reefhall_lobby.mtl','Assets/models/maps/reefhall/reefhall_lobby.obj','Assets/models/maps/reefhall/reefhall_lobby.vmdl','Tools/reefhall_map.py'}
assert set(changed)==allowed,changed
assert json.loads((ROOT/'Sources/ReefHall/bronze-planter-v1/review/installed.json').read_text())['Planters']==2
(OUT/'concurrent-changes.json').write_text(json.dumps(dict(reason='Approved bronze entrance planter installed independently; preserve current lobby and generator hook',files={p:sha(ROOT/p) for p in changed}),indent=2))
public=ROOT/'Assets/models/maps/reefhall/reefhall_filter.vmdl';source=ROOT/manifest['source'];original=public.read_text()
assert 'installed_wall_light.obj' not in original,'Already installed; inspect receipt'
before=OUT/'install-before';stage=OUT/'install-stage';dest=stage/'Assets/models/maps/reefhall/wall-light-v1';dest.mkdir(parents=True,exist_ok=True)
generator=ROOT/'Tools/reefhall_map.py'
for path in (public,source,generator):
 backup=before/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(path.read_bytes())
candidate=ROOT/'Assets/models/maps/reefhall/wall-light-v1/wall_light.obj'
obj=candidate.read_text().replace('mtllib wall_light.mtl','mtllib installed_wall_light.mtl')
obj=re.sub(r'(?m)^usemtl (.+)$',lambda m:'usemtl rh_wl_'+m[1],obj);(dest/'installed_wall_light.obj').write_text(obj)
mtl=re.sub(r'(?m)^newmtl (.+)$',lambda m:'newmtl rh_wl_'+m[1],candidate.with_suffix('.mtl').read_text());(dest/'installed_wall_light.mtl').write_text(mtl)
base=(candidate.parent/'filter_without_light.obj').read_text().replace('mtllib filter_without_light.mtl','mtllib '+source.with_suffix('.mtl').name)
target=stage/source.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(base)
own=candidate.with_suffix('.vmdl').read_text();pattern=r'\t{5}\{\n\t{6}_class = "RenderMeshFile".*?\n\t{5}\},'
node=re.search(pattern,own,re.S).group().replace('wall_light.obj','installed_wall_light.obj')
oldnode=re.search(pattern,original,re.S).group();merged=original.replace(oldnode,oldnode+'\n'+node,1)
remaps=[r.replace('from = "','from = "rh_wl_') for r in re.findall(r'\{ from = "[^\n]+?\}',own)]
assert not set(re.findall(r'from = "([^"]+)"','\n'.join(remaps)))&set(re.findall(r'from = "([^"]+)"',original))
index=merged.index('\t'*7+'{ from = ');merged=merged[:index]+'\n'.join('\t'*7+r+',' for r in remaps)+'\n'+merged[index:]
marker='_class = "PhysicsShapeList"';assert original[original.index(marker):]==merged[merged.index(marker):]
target=stage/public.relative_to(ROOT);target.parent.mkdir(parents=True,exist_ok=True);target.write_text(merged)
files={str(p.relative_to(stage)).replace('\\','/'):sha(p) for p in stage.rglob('*') if p.is_file()}
(OUT/'install-plan.json').write_text(json.dumps(dict(before={str(p.relative_to(ROOT)).replace('\\','/'):sha(p) for p in (public,source)},files=files,new_triangles=manifest['triangles'],old_triangles=manifest['original_triangles']),indent=2))
build=(HERE/'build.py').read_text();body=build[build.index('m=K.Model();X,Y,Z='):build.index('legacy=K.Model();')];body=body[:body.index(';count=K.write_model')]
helper='''"""Approved ReefHall wall light, exact prototype geometry and texture mapping."""
import math
import numpy as np
import map_kit as K
import reefhall_map as R
import riverdale_parts as G
import railhead_dress_detail as D
def model():
'''+''.join('    '+l+'\n' for l in body.splitlines())+'''    # Bake the prototype's projected and grain UVs before joining the room.
    offset=K.uv_offset('wall_light')
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
    m=model()
    for paint,faces in m.polygons.items():
        alias='rh_wl_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs[(paint,i)],normals=m.polygon_normals.get((paint,i)))
'''
(ROOT/'Tools/reefhall_wall_light.py').write_text(helper)
sys.path.insert(0,str(ROOT/'Tools'));import map_kit as K;import reefhall_wall_light as F
proof=OUT/'approved-generator.obj';K.write_obj(proof,F.model(),'wall_light');assert proof.read_text().splitlines()[3:]==candidate.read_text().splitlines()[3:]
assert not F.model().boxes and not F.model().hulls
g=generator.read_text()
old='    fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )'
assert g.count(old)==1
new='    if np.allclose(fr.p(u,w,z),(760.,1100.,110.)) and np.allclose(fr.vec(0,1,0),(0,1,0)):\n        from reefhall_wall_light import append_to as append_approved_wall_light\n        append_approved_wall_light(model)\n    else:\n        fbox( model, fr, u - 3.5, u + 3.5, w, w + 3.0, z, z + 16, { "default": "rh_gunmetal", "front": "rh_led_warm" } )'
g=g.replace(old,new);generator.write_text(g)

script=(ROOT/'Sources/Railhead/brick-pallet-v1/install.cs.txt').read_text().replace('output/railhead/brick-pallet-v1','output/reefhall/wall-light-v1').replace('Assets/models/maps/railhead/','Assets/models/maps/reefhall/').replace('InstalledPallets','InstalledLights');(HERE/'install.cs.txt').write_text(script)
print(json.dumps(dict(lights=1,staged_files=len(files),old_triangles=12,new_triangles=4300,generator_matches_approved=True)))
