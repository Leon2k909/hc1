"""Repack the ivy texture/UVs while preserving the accepted scene and geometry."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil
import numpy as np
import map_kit as K
import veridant_ivy as I

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/ivy-v2'
MODEL='Assets/models/maps/veridant/ivy-v2/ivy.obj'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--from-stage',default='stage-v4');parser.add_argument('--stage',default='stage-v5');parser.add_argument('--geometry-refresh',action='store_true');args=parser.parse_args()
    previous=OUT/args.from_stage;stage=OUT/args.stage;assert not stage.exists()
    manifest=json.loads((previous/'manifest.json').read_text())
    for relative,item in manifest['files'].items():assert sha(ROOT/relative)==item['after'],relative
    for group in ('protected_sha256',):
        for relative,value in manifest[group].items():assert sha(ROOT/relative)==value,relative
    for relative,value in manifest['source_sha256'].items():
        if relative not in ('Tools/veridant_ivy.py','Tools/veridant_revise_ivy.py'):assert sha(ROOT/relative)==value,relative
    stage.mkdir()
    shutil.copytree(previous/'Assets',stage/'Assets')
    model=K.Model()
    for at,right,w,h,seed,off in manifest['placements']:I.build_into(model,at,right,w,h,seed,off)
    K.write_obj(stage/MODEL,model,'veridant_ivy_v2')
    I.write_materials(stage/'Assets/materials/veridant/ivy-v2')
    # UVs may move in the padded canvas; positions, normals and face topology do not.
    old=(previous/MODEL).read_text().splitlines();new=(stage/MODEL).read_text().splitlines()
    if not args.geometry_refresh:
        for prefix in ('v ','vn ','f '):assert [x for x in old if x.startswith(prefix)]==[x for x in new if x.startswith(prefix)],prefix
    files={}
    for p in sorted((stage/'Assets').rglob('*')):
        if not p.is_file():continue
        relative=p.relative_to(stage);before=sha(ROOT/relative);backup=stage/'before'/relative
        if before:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/relative,backup)
        files[relative.as_posix()]={'before':before,'after':sha(p),'source':p.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    manifest.update(stage=args.stage,files=files,original_document=manifest.get('original_document',(previous/'before/Assets/models/maps/veridant/veridant_foliage.vmdl').relative_to(ROOT).as_posix()),
        geometry_positions_normals_faces_preserved=not args.geometry_refresh,texture_packing=json.loads((ROOT/'Sources/Veridant/ivy-v2/texture-packing.json').read_text()),
        new_triangles=model.triangle_count(),planting=model.ivy_stats)
    for relative in ('Tools/veridant_ivy.py','Tools/veridant_revise_ivy.py','Sources/Veridant/ivy-v2/leaf-packed.png','Sources/Veridant/ivy-v2/texture-packing.json'):
        manifest['source_sha256'][relative]=sha(ROOT/relative)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'stage':args.stage,'files':len(files),'triangles':model.triangle_count(),'geometry_preserved':not args.geometry_refresh,'packed_size':[2048,2048]}))


if __name__=='__main__':main()
