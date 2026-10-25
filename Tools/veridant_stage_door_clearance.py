"""Replace only the two doorway-blocking shelf assemblies in the live building OBJ."""
import hashlib
import argparse
import json
from pathlib import Path
import shutil
import map_kit as K
import veridant_map as V
import railhead_stage_extinguisher as Patch

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/door-obstruction'
STAGE=OUT/'stage-v1'


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def fixtures():
    old,new=K.Model(),K.Model()
    ranges={}
    for name,lo,hi,doors in (
        ('lounge',(-704.,-520.),(-692.,-300.),(V.LOUNGE_WEST_DOOR,)),
        ('cafe',(-704.,-120.),(-692.,120.),V.CAFE_WEST_DOORS)):
        V.P.counter_shelves(old,lo,hi,V.L0,face='+e')
        ranges[name]=V.shelves_beside_doors(new,lo,hi,V.L0,doors)
        for a,b in ranges[name]:
            for centre,width,bottom,top in doors:
                assert b<=centre-width/2-4 or a>=centre+width/2+4
    assert not old.boxes and not old.hulls and not new.boxes and not new.hulls
    V.configure(new)
    return old,new,ranges


def main():
    global STAGE
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',default='stage-v1')
    parser.add_argument('--target',default='Assets/models/maps/veridant/veridant_buildings.obj')
    args=parser.parse_args()
    assert args.stage.replace('-','').isalnum()
    relative=Path(args.target).as_posix()
    assert (ROOT/relative).resolve().is_relative_to((ROOT/'Assets/models/maps/veridant').resolve())
    assert relative.endswith('.obj')
    STAGE=OUT/args.stage
    assert not STAGE.exists(),'Preserve each staged revision.'
    STAGE.mkdir(parents=True)
    sources={p:sha(ROOT/p) for p in ('Tools/veridant_map.py','Tools/veridant_parts.py',
        'Tools/veridant_stage_door_clearance.py','Tools/map_kit.py','Tools/railhead_stage_extinguisher.py')}
    protected={p:sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
        'Assets/models/maps/veridant/veridant_buildings.vmdl',
        'Assets/models/maps/veridant/veridant_buildings.mtl',
        'Assets/models/maps/veridant/veridant_buildings_hulls_default.obj',
        'Assets/models/maps/veridant/veridant_buildings_hulls_metal.obj')}
    old,new,ranges=fixtures()
    piece=STAGE/'shelves.obj';K.write_obj(piece,new,'veridant_buildings')
    source=ROOT/relative;before=sha(source)
    backup=STAGE/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(source,backup);assert sha(backup)==before
    target=STAGE/relative;retained=STAGE/'retained-unrelated.obj'
    lookup,faces=Patch.lookup_polygons(old)
    result,found=Patch.replace_obj(source,target,retained,lookup,piece)
    Patch.coverage(found,lookup,faces)
    assert result['removed_triangles']==old.triangle_count()
    assert set(new.polygons)<=set(old.polygons)
    manifest={'revision':'veridant-door-clearance-v1','source_sha256':sources,'protected_sha256':protected,
        'files':{relative:{'before':before,'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
                           'backup':backup.relative_to(ROOT).as_posix()}},
        'doorways':{'lounge':V.LOUNGE_WEST_DOOR,'cafe':V.CAFE_WEST_DOORS},
        'shelf_ranges':ranges,'jamb_clearance_inches':4,'open_door_width_inches':60,
        'open_door_height_inches':96,'removed_triangles':old.triangle_count(),
        'new_triangles':new.triangle_count(),'unrelated_geometry_bytes_exact':True,
        'retained_sha256':sha(retained),'collision_unchanged':True,'scene_unchanged':True,
        'materials_unchanged':True}
    for group in (sources,protected):
        for path,digest in group.items():assert sha(ROOT/path)==digest,path
    assert sha(source)==before
    (STAGE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('revision','doorways','shelf_ranges','removed_triangles',
                                            'new_triangles','unrelated_geometry_bytes_exact','collision_unchanged')}))


if __name__=='__main__':main()
