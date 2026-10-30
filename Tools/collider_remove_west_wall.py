"""Stage one selected wing's concrete screen, its box collision and radar update."""
from collections import Counter
import argparse
import hashlib
import inspect
import json
from pathlib import Path
import platform
import re
import shutil
import numpy as np

platform._wmi_query=lambda *a,**k: (_ for _ in ()).throw(OSError('WMI unavailable during asset staging'))
import collider_map as C
import map_kit as K
import railhead_map as R

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/collider/wall-removal'
STAGE=OUT/'stage-v1'
OBJ='Assets/models/maps/collider/collider_structure.obj'
DOC='Assets/models/maps/collider/collider_structure.vmdl'
RADAR='Assets/ui/Minimaps/minimap_collider.png'
BOX=re.compile(r'\{\s*_class\s*=\s*"PhysicsShapeBox".*?\},?',re.S)
HULL=re.compile(r'\{\s*_class\s*=\s*"PhysicsHullFile".*?\},?',re.S)


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def vector(text,key):return np.array([float(x) for x in re.search(r'\b'+key+r'\s*=\s*\[([^]]+)\]',text)[1].split(',')])
def plan(world):return np.array((-world[1],world[0],world[2]))


def collision(text):
    model=K.Model()
    for match in BOX.finditer(text):
        body=match[0];rotation=K.rotation_matrix(*vector(body,'angles'))
        surface=re.search(r'surface_prop\s*=\s*"([^"]+)"',body)[1]
        model.boxes.append((plan(vector(body,'origin')),[plan(rotation[:,i]) for i in range(3)],vector(body,'dimensions'),surface))
    for match in HULL.finditer(text):
        body=match[0];name=re.search(r'filename\s*=\s*"([^"]+)"',body)[1]
        surface=re.search(r'surface_prop\s*=\s*"([^"]+)"',body)[1]
        points=[None];faces=[]
        for line in (ROOT/'Assets'/name).open():
            if line.startswith('v '):
                x,y,z=map(float,line.split()[1:]);points.append(np.array((-x,z,y)))
            elif line.startswith('f '):faces.append([int(v) for v in line.split()[1:]])
        parents=list(range(len(points)))
        def find(i):
            while parents[i]!=i:parents[i]=parents[parents[i]];i=parents[i]
            return i
        for face in faces:
            for v in face[1:]:parents[find(v)]=find(face[0])
        groups={}
        for i in range(1,len(points)):groups.setdefault(find(i),[]).append(points[i])
        model.hulls.extend((p,surface) for p in groups.values())
    return model


def record(relative,extra=None):
    source=ROOT/relative;backup=STAGE/'before'/relative
    backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,backup)
    return {'before':sha(source),'after':sha(STAGE/relative),'source':(STAGE/relative).relative_to(ROOT).as_posix(),
        'backup':backup.relative_to(ROOT).as_posix(),**(extra or {})}


def main():
    global OUT,STAGE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--side',choices=('west','east'),default='west')
    args=parser.parse_args()
    side=-1 if args.side=='west' else 1
    if args.side=='east':OUT=ROOT/'output/collider/wall-removal-east';STAGE=OUT/'stage-v1'
    STAGE.mkdir(parents=True,exist_ok=False)
    e0,e1=sorted((side*1500,side*1524))
    old=K.Model();C.box(old,e0,e1,-160,160,0,164,'co_concrete')
    wanted=Counter()
    for paint,rows in old.polygons.items():
        for pts,normal in rows:
            p=[K.obj_vector(K.to_world(v)).encode() for v in pts]
            for i in range(1,len(p)-1):wanted[(paint.encode(),frozenset((p[0],p[i],p[i+1])))]+=1
    positions=set().union(*(pts for paint,pts in wanted));sparse={};count=0;paint=None;found=Counter();removed=[]
    target=STAGE/OBJ;target.parent.mkdir(parents=True)
    with target.open('wb') as output:
        for number,line in enumerate((ROOT/OBJ).open('rb')):
            if line.startswith(b'v '):
                count+=1;p=line[2:].strip()
                if p in positions:sparse[count]=p
            elif line.startswith(b'usemtl '):paint=line.split()[1]
            elif line.startswith(b'f ') and paint==b'co_concrete':
                ids=[int(token.split(b'/')[0]) for token in line.split()[1:]]
                if all(i in sparse for i in ids):
                    key=(paint,frozenset(sparse[i] for i in ids))
                    if key in wanted:found[key]+=1;removed.append(number);continue
            output.write(line)
    assert found==wanted and len(removed)==12
    original=(ROOT/DOC).read_bytes().decode('utf8');matches=[]
    for match in BOX.finditer(original):
        if np.allclose(vector(match[0],'origin'),(0,-side*1512,82)) and np.allclose(vector(match[0],'dimensions'),(24,320,164)):
            matches.append(match)
    assert len(matches)==1
    match=matches[0];updated=original[:match.start()]+original[match.end():]
    assert len(list(BOX.finditer(original)))-len(list(BOX.finditer(updated)))==1
    (STAGE/DOC).write_bytes(updated.encode('utf8'))
    others=(ROOT/'Assets/models/maps/collider/collider_detail.vmdl').read_text()
    before_models=[collision(original),collision(others)];after_models=[collision(updated),collision(others)]
    assert len(before_models[0].boxes)-len(after_models[0].boxes)==1
    C.STAGE=STAGE/'radar-before';C.minimap(before_models)
    # Require a faithful round trip of the published collision before replacing
    # the radar, so another map change cannot be silently regenerated away.
    from PIL import Image
    reference=C.STAGE/'ui/minimaps/minimap_collider.png'
    with Image.open(reference) as a,Image.open(ROOT/RADAR) as b:
        assert a.size==b.size and np.array_equal(np.array(a),np.array(b)),'Published radar differs; inspect before replacing.'
    C.STAGE=STAGE/'Assets';C.minimap(after_models)
    files={OBJ:record(OBJ,{'removed_face_lines':removed,'removed_triangles':12,'all_other_obj_bytes_exact':True}),
        DOC:record(DOC,{'removed_collision_boxes':1,'removed_node':match[0],'all_other_modeldoc_bytes_exact':True}),RADAR:record(RADAR)}
    scene='Assets/scenes/maps/Collider/collider.scene'
    protected=[scene,'Assets/models/maps/collider/collider_structure.mtl',
        'Assets/models/maps/collider/collider_structure_hulls_metal.obj']
    protected += [p.relative_to(ROOT).as_posix() for p in (ROOT/'Assets/models/maps/collider').iterdir()
        if p.suffix in ('.obj','.mtl','.vmdl') and p.name.startswith(('collider_detail','collider_glass','collider_machine'))]
    manifest={'revision':f'collider-{args.side}-spawn-wall-removal-v1','walls_removed':1,'plan_bounds':[e0,e1,-160,160,0,164],
        'files':files,'protected_sha256':{p:sha(ROOT/p) for p in protected},
        'source_sha256':{p:sha(ROOT/p) for p in ('Tools/collider_map.py','Tools/collider_remove_west_wall.py','Tools/map_kit.py')},
        'generator_hook':inspect.getsource(C.wings),'radar_before_matches_published_pixels':True}
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # A removed obstacle cannot create a new clearance/support/reach obstruction.
    # Run the authored clearance and reach checks against the actual published
    # physics representation, rather than regenerating unrelated render assets.
    problems=R.check_spots(R.collision_aabbs(after_models),C.all_spots())
    reach=R.check_reach(after_models,C.all_spots(),OUT/'reach-after.png',bounds=C.PLAY)
    before_seen=R.check_retakes_sight(R.Blockers(before_models),C.RETAKES)
    after_seen=R.check_retakes_sight(R.Blockers(after_models),C.RETAKES)
    checks={'checked_spots':len(C.all_spots()),'obstructed_or_unsupported':problems,'unreachable':reach,
        'retakes_exposed_pairs_before':before_seen,'retakes_exposed_pairs_after':after_seen}
    (OUT/'layout-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
    assert problems==0 and reach==0,checks
    print(json.dumps({'walls_removed':1,'removed_triangles':12,'collision_boxes_removed':1,'files':len(files),'layout':checks}),flush=True)


if __name__=='__main__':main()
