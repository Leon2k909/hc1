"""Raise only Belltower's mirrored VIA DELLE MURA slabs above their stonework."""
import hashlib
import json
from pathlib import Path
import re
import shutil

import belltower_architecture as A
import belltower_map as B
from belltower_safe_imports import span
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/street-sign-clearance-v1'
STAGE = OUT/'stage'
RISE = 24.0


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def in_slab(point, side):
    x, height, n = point  # OBJ axes: west, up, north.
    low, high = (1850,1851) if side == 'west' else (-1851,-1850)
    return low-1e-5<=x<=high+1e-5 and 110-1e-5<=height<=119+1e-5 and 364-1e-5<=n<=388+1e-5


def stage_slab(source, side):
    selected = {}
    vertex = 0
    for number, line in enumerate(source.open('rb')):
        if line.startswith(b'v '):
            vertex += 1
            point = tuple(map(float, line.split()[1:]))
            if in_slab(point, side):
                selected[vertex] = (number, point)
    if not selected:
        return None
    material = None
    affected = {}
    used = set()
    triangles = 0
    for line in source.open('rb'):
        if line.startswith(b'usemtl '):
            material = line.split()[1].decode()
        elif line.startswith(b'f '):
            indices = [int(t.split(b'/')[0]) for t in line.split()[1:]]
            triangles += 1
            touched = set(indices)&selected.keys()
            if touched:
                assert touched == set(indices), ('Shared non-plaque vertex', source, indices)
                assert material in ('ashlar', 'plaque_7'), (source, material)
                affected[material] = affected.get(material, 0)+1
                used.update(indices)
    assert used == selected.keys(), ('Unused or shared slab vertices', source)
    assert affected in ({'ashlar':10,'plaque_7':2}, {'ashlar':10}, {'plaque_7':2}), (source, affected)
    relative = source.relative_to(ROOT)
    target, backup = STAGE/relative, OUT/'before'/relative
    assert not target.exists() and not backup.exists()
    target.parent.mkdir(parents=True, exist_ok=True)
    backup.parent.mkdir(parents=True, exist_ok=True)
    before = sha(source)
    shutil.copyfile(source, backup)
    edits = {number:point for number,point in selected.values()}
    preserved = hashlib.sha256()
    with target.open('wb') as output:
        for number,line in enumerate(source.open('rb')):
            if number in edits:
                x,z,n = edits[number]
                ending = b'\r\n' if line.endswith(b'\r\n') else b'\n'
                output.write(f'v {x:.3f} {z+RISE:.3f} {n:.3f}'.encode()+ending)
            else:
                output.write(line)
                preserved.update(line)
    # The same face, UV and normal records survive byte for byte; only the
    # vertices used exclusively by this slab move vertically.
    after_preserved = hashlib.sha256()
    with source.open('rb') as old, target.open('rb') as new:
        for number,(a,b) in enumerate(zip(old,new,strict=True)):
            if number in edits:
                p,q = list(map(float,a.split()[1:])),list(map(float,b.split()[1:]))
                assert q == [p[0],p[1]+RISE,p[2]]
            else:
                assert a == b
                after_preserved.update(b)
    assert after_preserved.digest()==preserved.digest() and sha(source)==before and sha(backup)==before
    return {'source':target.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix(),
            'before':before,'after':sha(target),'moved_vertices':len(edits),
            'affected_triangles':affected,'triangles_before':triangles,'triangles_after':triangles,
            'only_plaque_vertices_moved':True,'all_unrelated_source_bytes_preserved':True,
            'unrelated_source_bytes_sha256':preserved.hexdigest()}


def placement_check():
    wall = B.face_wall(-1850,-1400,350,600,'-e',0,300,corners=True)
    wall.add(350+250/6,44,34,104,'glass')
    wall.add(350+250/6,42,164,236,'glass')
    decoration = K.Model()
    A.window_surround(decoration,wall,wall.openings[0],'ashlar',variant=2)
    B.bands(decoration,wall,[124],'ashlar')
    plaque = K.Model()
    assert B.street_plaque(plaque,wall,0,'plaque_7')
    points = [p for polygons in plaque.polygons.values() for polygon,_ in polygons for p in polygon]
    assert min(p[2] for p in points)==134 and max(p[2] for p in points)==143
    assert not plaque.boxes and not plaque.hulls and not plaque.props
    assert (364,388,134,143) in wall.fixtures
    return {'old_bottom':110,'new_bottom':134,'new_top':143,'floor_band_top':130,
            'vertical_gap_above_band_inches':4,'window_hood_and_slab_clear':True}


def main():
    assert not (STAGE/'manifest.json').exists(), 'Preserve existing evidence.'
    STAGE.mkdir(parents=True,exist_ok=True)
    result = {'revision':'street-sign-clearance-v1','placement':placement_check(),
              'files':{},'source_sha256':{},'protected_sha256':{},
              'only_street_plaque_slabs_changed':True,'scene_changed':False,'physics_changed':False}
    protected = set()
    for side in ('west','east'):
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        vmdl = canonical.with_suffix('.vmdl')
        text = vmdl.read_text()
        lo,hi = span(text, '_class = "RenderMeshList"')
        render_refs = [ROOT/'Assets'/s for s in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text[lo:hi])]
        all_refs = [ROOT/'Assets'/s for s in re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text)]
        candidates = [p for p in render_refs if p.stem.endswith(('_ashlar','_plaque_7'))]
        found = []
        for path in [canonical,*candidates]:
            row = stage_slab(path, side)
            if row:
                result['files'][path.relative_to(ROOT).as_posix()] = row
                found.append(row['affected_triangles'])
        assert len(found)==3 and {'ashlar':10,'plaque_7':2} in found and {'ashlar':10} in found and {'plaque_7':2} in found
        protected.update([vmdl,canonical.with_suffix('.mtl'),*all_refs])
    protected.add(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
    for path in sorted(protected):
        if path.relative_to(ROOT).as_posix() not in result['files']:
            result['protected_sha256'][path.relative_to(ROOT).as_posix()] = sha(path)
    for relative in ('Tools/belltower_map.py','Tools/belltower_architecture.py','Tools/belltower_stage_street_sign.py'):
        result['source_sha256'][relative] = sha(ROOT/relative)
    assert len(result['files'])==6
    (STAGE/'manifest.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'files':{p:dict(vertices=r['moved_vertices'],triangles=r['affected_triangles']) for p,r in result['files'].items()},
                      'placement':result['placement'],'protected_files':len(result['protected_sha256'])},indent=2))


if __name__=='__main__':
    main()
