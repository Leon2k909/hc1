"""Stage a separate, render-only rear-wall asset; never rebuild the shared hall."""
import hashlib
import inspect
import json
from pathlib import Path
import shutil
import numpy as np
import ares_map as A
import map_kit as K
from ares_stair_cladding import append_rear_closure

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'output/ares/stair-rear-wall'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    stage=OUT/'stage-v1';stage.mkdir(parents=True,exist_ok=False)
    model=K.Model();parts=[]
    for tag,across,run in (('hall',A.STAIR_E,A.STAIR_N),('wing',A.WING_STAIR_E,A.WING_STAIR_N)):
        for sign in (-1,1):
            c0,c1=sorted((sign*across[0],sign*across[1]))
            old_count={p:len(rows) for p,rows in model.polygons.items()}
            detail=append_rear_closure(model,'n',c0,c1,*run,0,A.G,A.DT)
            points=np.vstack([pts for paint,rows in model.polygons.items() for pts,n in rows[old_count.get(paint,0):]])
            r=A.G/round(A.G/7.4)
            roof=.5*r+(A.G-.5*r)*(points[:,1]-run[0])/(run[1]-run[0])
            assert np.isfinite(points).all() and points[:,0].min()>=c0 and points[:,0].max()<=c1
            assert points[:,1].min()>=run[0] and points[:,1].max()<run[1]
            assert np.all(points[:,2]<=roof+1e-6) and points[:,2].min()>=-.35-1e-6
            parts.append(dict(name=tag+('-west' if sign<0 else '-east'),**detail))
    assert not model.boxes and not model.hulls
    A.configure(model)
    folder=stage/'Assets/models/maps/ares/stair-rear-wall';folder.mkdir(parents=True)
    name='ares_stair_rear_closures';resource='models/maps/ares/stair-rear-wall'
    K.write_obj(folder/(name+'.obj'),model,name)
    K.write_vmdl(folder/(name+'.vmdl'),resource,name,model)
    files={}
    for file in folder.iterdir():
        path=file.relative_to(stage).as_posix();assert not (ROOT/path).exists()
        files[path]=dict(source=file.relative_to(ROOT).as_posix(),sha256=sha(file))
    protected={p:sha(ROOT/p) for p in ('Assets/models/maps/ares/ares_hall.vmdl','Assets/models/maps/ares/ares_hall.obj',
        'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj','Assets/scenes/maps/Ares/ares.scene')}
    scene=ROOT/'Assets/scenes/maps/Ares/ares.scene';shutil.copy2(scene,OUT/'scene-before.scene')
    manifest=dict(files=files,protected=protected,parts=parts,triangles=model.triangle_count(),
        source_sha256={p:sha(ROOT/p) for p in ('Tools/ares_stair_cladding.py','Tools/ares_stage_stair_cladding.py')},
        stair_source=inspect.getsource(A.stair),model=resource+'/'+name+'.vmdl')
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'compile-request.json').write_text(json.dumps({'path':manifest['model'],'full':False}))
    (OUT/'spawn-request.json').write_text(json.dumps(dict(model=manifest['model'],name='Stair Rear Closures',
        parent='494b3138-552e-593d-abb5-0b70629de683',position='0,0,0',angles='0,0,0',scale='1')))
    print(json.dumps(dict(parts=len(parts),triangles=model.triangle_count(),colliders=0)))


if __name__=='__main__':main()
