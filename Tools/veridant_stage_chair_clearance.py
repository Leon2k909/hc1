"""Replace only Veridant's chair imports with rear-mounted, clear supports."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil

import numpy as np

import map_kit as K
import veridant_chair as C
import veridant_materials as VM
from belltower_safe_imports import span
from veridant_stage_chairs import placements, replace

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/veridant/chair-v3'
STAGE = OUT/'stage-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream,'sha256').hexdigest()


def clearance(module):
    model = K.Model()
    module.build_into(model,(0,0),(1,0))
    points = np.array([p for pts,n in model.polygons['vr_steel'] for p in pts])
    x,y,z = points.T
    back_x = -7.05-.125*(z-19.3)+.0155*y*y
    mask = (np.abs(y)<7.25)&(z>19.3)&(z<33.1)
    distance = (x-back_x)/np.sqrt(1+(.031*y)**2+.125**2)
    # Back skin is 0.24 inches behind its centre surface. Mounting caps finish
    # farther behind that skin, including their entire circular cross section.
    bad = int((mask&(distance>-.24)).sum())
    result = {'steel_vertices_inside_back':bad,
              'minimum_back_gap_mm':float((-distance[mask].max()-.24)*25.4)}
    seat_z = 17.45+.003*x*x+.004*y*y+.018*x
    dx = np.maximum(np.abs(x-.1)-5.8,0)
    dy = np.maximum(np.abs(y)-5.85,0)
    within_seat = (dx*dx+dy*dy<1.8**2)&(x>-7.5)&(x<7.7)&(np.abs(y)<7.65)
    result['steel_vertices_inside_seat'] = int((within_seat&(np.abs(z-seat_z)<.239)).sum())
    return result


def main():
    assert not STAGE.exists(), 'Preserve each staged revision'
    STAGE.mkdir(parents=True)
    old_spec = importlib.util.spec_from_file_location('legacy_chair',ROOT/'Sources/Veridant/chair-v3/legacy_chair.py')
    legacy = importlib.util.module_from_spec(old_spec)
    old_spec.loader.exec_module(legacy)
    checks = {'before':clearance(legacy),'after':clearance(C)}
    assert checks['after']['steel_vertices_inside_back']==0
    assert checks['after']['steel_vertices_inside_seat']==0
    assert checks['after']['minimum_back_gap_mm']>.3
    canonical = Path('Assets/models/maps/veridant/veridant_dress.obj')
    vmdl = canonical.with_suffix('.vmdl')
    document = (ROOT/vmdl).read_text()
    before = {str(p):sha(ROOT/p) for p in (canonical,vmdl)}
    rows = placements()
    old,new = K.Model(),K.Model()
    for at,facing,z0 in rows:
        legacy.build_into(old,at,facing,z0)
        C.build_into(new,at,facing,z0)
    new.tile_overrides = {paint:VM.TILES.get(paint,64.) for paint in new.polygons}
    piece = STAGE/'all-chairs.obj'
    K.write_obj(piece,new,'veridant_chairs_v3')
    output = STAGE/canonical
    output.parent.mkdir(parents=True)
    replacement = replace(ROOT/canonical,output,old,piece)
    paths = [canonical]
    chunks = []
    for start in range(0,len(rows),6):
        chunk = K.Model()
        for at,facing,z0 in rows[start:start+6]:
            C.build_into(chunk,at,facing,z0)
        chunk.tile_overrides = {paint:VM.TILES.get(paint,64.) for paint in chunk.polygons}
        relative = Path(f'Assets/models/maps/veridant/chair-v3/chairs-{start//6}.obj')
        target = STAGE/relative
        target.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(target,chunk,target.stem)
        counts = Counter(l.split()[0] for l in target.open() if l.startswith(('v ','vt ','vn ')))
        assert max(counts.values())<65536,counts
        paths.extend([relative,relative.with_suffix('.mtl')])
        old_path = f'models/maps/veridant/chair-v2/chairs-{start//6}.obj'
        assert document.count(old_path)==1, 'Chair import has changed; inspect before replacing'
        document = document.replace(old_path,relative.relative_to('Assets').as_posix())
        chunks.append(relative.relative_to('Assets').as_posix())
    original = (ROOT/vmdl).read_text()
    a,b = span(original,'_class = "PhysicsShapeList"')
    c,d = span(document,'_class = "PhysicsShapeList"')
    assert original[a:b]==document[c:d]
    (STAGE/vmdl).write_text(document)
    paths.append(vmdl)
    files = {}
    for relative in paths:
        target = ROOT/relative
        old_hash = before.get(str(relative),sha(target) if target.exists() else None)
        if old_hash:
            assert sha(target)==old_hash, ('Shared file changed',str(relative))
            backup = STAGE/'before'/relative
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(target,backup)
        files[relative.as_posix()] = {'before':old_hash,'after':sha(STAGE/relative),
                                     'source':(STAGE/relative).relative_to(ROOT).as_posix()}
    a,b = span(original,'_class = "RenderMeshList"')
    imports = [ROOT/'Assets'/p for p in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',original[a:b])]
    protected_paths = [ROOT/'Assets/scenes/maps/Veridant/veridant.scene',
                       ROOT/'Assets/materials/veridant/vr_wicker.vmat',*imports,
                       *(ROOT/'Assets/models/maps/veridant').glob('veridant_dress_hulls_*.obj')]
    protected = {p.relative_to(ROOT).as_posix():sha(p) for p in protected_paths}
    single = K.Model()
    C.build_into(single,(0,0),(1,0))
    manifest = {'revision':'veridant-chair-clearance-v3','files':files,'protected':protected,
                'instances':len(rows),'triangles_per_chair':single.triangle_count(),
                'chair_imports':chunks,'physics_bytes_exact':True,'geometry_checks':checks,
                'replacement':replacement,
                'placements':[{'at':at.tolist(),'facing':facing.tolist(),'z0':z0} for at,facing,z0 in rows]}
    for relative,data in files.items():
        target = ROOT/relative
        assert (sha(target) if target.exists() else None)==data['before'],relative
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'capture-request.json').write_text(json.dumps({'stage':'stage-v1','phase':'after'}))
    print(json.dumps({'instances':len(rows),'triangles_per_chair':single.triangle_count(),'checks':checks,
                      'files':len(files),'physics_unchanged':True}))


if __name__=='__main__':
    main()
