"""Stage only the spa's two facade faces and nine replacement windows."""
import argparse
import inspect
import json
from pathlib import Path
import re
import shutil

import numpy as np
import map_kit as K
import veridant_map as V
import veridant_spa_windows as W
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/spa-windows-v2'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',required=True)
    args=parser.parse_args();assert re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    sources={p:Patch.sha(ROOT/p) for p in ('Tools/veridant_spa_windows.py','Tools/veridant_stage_spa_windows.py',
        'Tools/riverdale_parts.py','Tools/map_kit.py','Tools/railhead_stage_extinguisher.py')}
    snippets={'Tools/veridant_map.py':[inspect.getsource(V.spa),
         'if paint.startswith( "vr_spa_" ) and paint in model.material_overrides:']}
    document=Path('Assets/models/maps/veridant/veridant_buildings.vmdl');raw=(ROOT/document).read_text()
    a,b=span(raw,'_class = "RenderMeshList"');render=raw[a:b]
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
    first='spa-windows-v2/' not in render
    base=Path('Assets')/next(p for p in imports if p.endswith('veridant_buildings-base.obj'))
    protected={p:Patch.sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
          'Assets/models/maps/veridant/veridant_buildings.obj','Assets/models/maps/veridant/veridant_glass.vmdl')}
    for path in imports:
        p='Assets/'+path
        if p!=base.as_posix() and '/spa-windows-v2/' not in p:protected[p]=Patch.sha(ROOT/p)
    if not first:protected[document.as_posix()]=Patch.sha(ROOT/document)
    files={}
    def record(relative):
        relative=Path(relative);live=ROOT/relative;target=stage/relative
        before=Patch.sha(live) if live.exists() else None;backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,backup)
            assert Patch.sha(backup)==before
        files[relative.as_posix()]={'before':before,'after':Patch.sha(target),
            'source':target.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    material=Path('Assets/materials/veridant/spa-windows-v2');W.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()):record(p.relative_to(stage))
    new=K.Model();details=W.build_facades(new,V.SPA,V.SPA_TOP)
    W.washer_faces(new,V.SPA);V.configure(new)
    assert len(details)==9 and sum(s['lit'] for s in details)==4
    assert not new.boxes and not new.hulls
    assert 10000<new.triangle_count()<55000,new.triangle_count()
    for paint,rows in new.polygons.items():
        for i,(points,normals) in enumerate(rows):
            assert np.isfinite(points).all() and np.isfinite(normals).all()
            if (paint,i) in new.polygon_normals:assert np.isfinite(new.polygon_normals[(paint,i)]).all()
    piece=Path('Assets/models/maps/veridant/spa-windows-v2/spa-facades.obj')
    (stage/piece).parent.mkdir(parents=True,exist_ok=True)
    new.uv_source_name='veridant_buildings'
    K.write_obj(stage/piece,new,'veridant_buildings');record(piece);record(piece.with_suffix('.mtl'))
    old=K.Model()
    if first:W.legacy_faces(old,V.SPA,V.SPA_TOP)
    W.washer_faces(old,V.SPA,old=True)
    removed=224 if first else 16
    assert old.triangle_count()==removed,old.triangle_count()
    lookup,polygons=Patch.lookup_polygons(old)
    result,found=Patch.replace_obj(ROOT/base,stage/'proof/combined.obj',stage/base,lookup,stage/piece)
    Patch.coverage(found,lookup,polygons);assert result['removed_triangles']==removed
    record(base)
    i,j=span(render,'_class = "RenderMeshFile"');node=render[i:j]
    node=re.sub(r'name = "[^"]+"','name = "veridant_spa_windows_v2"',node,count=1)
    node=re.sub(r'filename = "[^"]+"',f'filename = "{piece.relative_to("Assets").as_posix()}"',node,count=1)
    end=render.rfind(']');prefix=render[:end].rstrip()
    replacement=prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[end:]
    updated=raw[:a]+replacement+raw[b:]
    remaps=''.join(f'{{ from = "{p}.vmat" to = "{m}" }},\n' for p,m in W.MATERIALS.items())
    i=updated.index('[',updated.index('remaps ='))+1;updated=updated[:i]+'\n'+remaps+updated[i:]
    marker='_class = "PhysicsShapeList"'
    assert raw[raw.index(marker):]==updated[updated.index(marker):]
    if first:
        (stage/document).write_text(updated);record(document)
    manifest={'revision':'veridant-spa-windows-v2','stage':args.stage,'files':files,'source_sha256':sources,
        'required_source_snippets':snippets,'protected_sha256':protected,'base_import':base.as_posix(),
        'windows':details,'windows_updated':9,'new_triangles':new.triangle_count(),
        'spa_rect':list(V.SPA),'spa_top':V.SPA_TOP,**result,
        'physics_bytes_exact':True,'scene_unchanged_at_asset_import':True,'other_render_imports_preserved':True,
        'replaces_previous_own_import':not first,'four_existing_lights_require_lowering':True}
    (stage/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (sources,protected):
        for p,h in group.items():assert Patch.sha(ROOT/p)==h,('Shared input changed',p)
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source'])==item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Shared target changed',p)
    for p,parts in snippets.items():
        text=(ROOT/p).read_text();assert all(part in text for part in parts)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'windows':9,'lit_windows':4,'new_triangles':new.triangle_count(),
                      'removed_triangles':removed,'files':len(files),'physics_and_unrelated_geometry_preserved':True}))


if __name__=='__main__':main()
