"""Stage one detailed, reusable lab-door leaf; never regenerate Collider's map."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
import map_kit as K
import riverdale_parts as P

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/collider/automatic-door'
RESOURCE='models/maps/collider/automatic-door-v1'
AXES=np.eye(3)


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='stage-v1');args=parser.parse_args()
    assert args.stage.replace('-','').isalnum() and args.stage.startswith('stage-')
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    model=K.Model()
    # Plan east becomes model -Y; plan north becomes model +X.
    P.bevel_box(model,(0,0,0),AXES,(87.5,8,188),'body',bevel=.65,surface='metal')
    for side in (-1,1):
        P.bevel_box(model,(0,side*4.32,18),AXES,(76,.8,126),'frame',bevel=.32)
        P.bevel_box(model,(0,side*4.78,18),AXES,(72,.3,122),'panel',bevel=.18)
        for e in (-22,0,22):
            P.bevel_box(model,(e,side*5.02,24),AXES,(1.15,.32,94),'dark',bevel=.12)
        P.bevel_box(model,(0,side*4.6,-73),AXES,(78,1,25),'kick',bevel=.4)
        for e in (-35,35):
            for z in (-76,0,74):
                P.lathe_axis(model,(e,side*5.0,z),(0,side,0),[(.46,0),(.46,.18),(.34,.24)],'steel',sides=8,cap='steel')
        # A small recessed service panel keeps the automatic leaf recognisable.
        P.bevel_box(model,(-26,side*5.08,-30),AXES,(12,.5,18),'dark',bevel=.7)
        for z in (-34,-30,-26):
            P.bevel_box(model,(-26,side*5.38,z),AXES,(6,.15,.55),'steel',bevel=.12)
    P.bevel_box(model,(43.76,0,0),AXES,(.38,8.2,183),'rubber',bevel=.1)
    model.material_overrides.update({
        'body':'materials/ares/pressure-doors-v3/body.vmat',
        'panel':'materials/ares/pressure-doors-v3/panel.vmat',
        'frame':'materials/collider/co_trim.vmat','dark':'materials/collider/co_rubber.vmat',
        'kick':'materials/ares/pressure-doors-v3/kick.vmat','steel':'materials/collider/co_silver.vmat',
        'rubber':'materials/collider/co_rubber.vmat'})
    model.tile_overrides.update({p:32. for p in model.polygons})
    assert len(model.boxes)==1 and not model.hulls
    # The meeting seals overlap physically by .2 inches when shut: a ray
    # through the exact centre seam must not pass through a closed door.
    centre,axes,size,surface=model.boxes[0]
    model.boxes[0]=(centre,axes,np.array((88.2,8,188)),surface)
    for material in model.material_overrides.values():assert (ROOT/'Assets'/material).is_file(),material
    dest=stage/'Assets'/RESOURCE
    triangles=K.write_model(dest,RESOURCE,'lab_door_leaf',model)
    files={}
    for path in sorted(dest.iterdir()):
        relative=path.relative_to(stage).as_posix();target=ROOT/relative
        before=sha(target) if target.exists() else None;backup=stage/'before'/relative
        if before:backup.parent.mkdir(parents=True,exist_ok=True);backup.write_bytes(target.read_bytes())
        files[relative]={'source':path.relative_to(ROOT).as_posix(),'after':sha(path),'before':before,
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    manifest={'revision':'collider-automatic-door-v1','files':files,'triangles_per_leaf':triangles,
        'leaf_model':RESOURCE+'/lab_door_leaf.vmdl','door_world_position':[0,1412,0],'door_world_yaw':90,
        'width':176,'height':192,'materials':model.material_overrides,
        'source_sha256':{p:sha(ROOT/p) for p in ('Tools/collider_automatic_door.py','Code/World/AutomaticSlidingDoor.cs')},
        'scene_sha256_before':sha(ROOT/'Assets/scenes/maps/Collider/collider.scene')}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Preserve the pre-task map before any editor scene operation.
    if not (OUT/'before-collider.scene').exists():
        (OUT/'before-collider.scene').write_bytes((ROOT/'Assets/scenes/maps/Collider/collider.scene').read_bytes())
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage}))
    (OUT/'compile-model.json').write_text(json.dumps({'path':manifest['leaf_model'],'full':False}))
    print(json.dumps({'triangles_per_leaf':triangles,'new_assets':len(files),'world_position':manifest['door_world_position']}))


if __name__=='__main__':main()
