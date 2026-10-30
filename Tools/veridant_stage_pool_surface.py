"""Stage a pool-only shader/material revision without rebuilding shared meshes."""
import argparse
import json
from pathlib import Path
import shutil
import railhead_stage_extinguisher as Patch
import veridant_pool_detail as Detail

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/pool-v2'


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--stage',required=True)
    args=parser.parse_args();assert args.stage.startswith('stage-') and args.stage.replace('-','').isalnum()
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    document=ROOT/'Assets/models/maps/veridant/veridant_dress.vmdl'
    assert 'models/maps/veridant/pool-v2/pool.obj' in document.read_text()
    files={}
    pairs=(('Sources/Veridant/pool-v2/water.shader','Assets/shaders/hc1_veridant_pool_v2.shader'),)
    for source,target in pairs:
        dest=stage/target;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/source,dest)
        backup=stage/'before'/target;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/target,backup)
        files[target]={'before':Patch.sha(backup),'after':Patch.sha(dest),
                       'source':dest.relative_to(ROOT).as_posix(),'backup':backup.relative_to(ROOT).as_posix()}
    manifest={'revision':'veridant-pool-v2','stage':args.stage,'files':files,
        'source_sha256':{p:Patch.sha(ROOT/p) for p in ('Tools/veridant_stage_pool_surface.py',
            'Sources/Veridant/pool-v2/water.shader','Tools/veridant_pool_detail.py')},
        'required_source_snippets':{},'protected_sha256':{p:Patch.sha(ROOT/p) for p in (
            'Assets/models/maps/veridant/pool-v2/pool.obj',
            'Assets/materials/veridant/vr_pool.vmat',
            'Assets/models/maps/veridant/veridant_dress_hulls_default.obj',
            'Assets/models/maps/veridant/veridant_dress_hulls_metal.obj')},
        'base_import':'Assets/models/maps/veridant/chair-v2/dress-base.obj',
        'geometry_unchanged':True,'collision_exact':True}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'stage':args.stage,'files':len(files),'geometry_unchanged':True}))


if __name__=='__main__':main()
