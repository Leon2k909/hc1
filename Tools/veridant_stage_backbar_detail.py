"""Stage the next back-bar pass using its existing dedicated mesh imports."""
import argparse
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_backbar as B
from veridant_stage_backbar import units
from railhead_stage_extinguisher import sha
from belltower_safe_imports import span

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'output/veridant/backbar-v2'


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--stage',required=True);args=ap.parse_args()
    assert re.fullmatch(r'stage-[a-z0-9-]+',args.stage)
    stage=OUT/args.stage;stage.mkdir(exist_ok=False,parents=True)
    sources={p:sha(ROOT/p) for p in ('Tools/veridant_backbar.py','Tools/veridant_backbar_detail.py',
        'Tools/veridant_stage_backbar_detail.py','Tools/map_kit.py','Tools/riverdale_parts.py',
        'Sources/Veridant/backbar-v2/walnut-albedo-generated.png',
        'Sources/Veridant/backbar-v2/lighting-installed.json')}
    import veridant_map as V
    snippets={'Tools/veridant_parts.py':[inspect.getsource(P.counter_shelves)],
              'Tools/veridant_map.py':[inspect.getsource(V.probe_object)]}
    configure=(ROOT/'Tools/veridant_map.py').read_text()
    assert re.search(r'paint\.startswith\(\s*\(\s*[\'"]vr_backbar_[\'"]',configure)
    specs=units();assert len(specs)==3
    document='Assets/models/maps/veridant/veridant_buildings.vmdl'
    raw=(ROOT/document).read_text();a,b=span(raw,'_class = "RenderMeshList"')
    imports=re.findall(r'filename\s*=\s*"([^"]+\.obj)"',raw[a:b])
    pieces=[f'Assets/models/maps/veridant/backbar-v1/shelves-{i}.obj' for i in range(3)]
    assert all(p[7:] in imports for p in pieces)
    protected={p:sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',)}
    unrelated={'Assets/models/maps/veridant/veridant_buildings.obj':sha(ROOT/'Assets/models/maps/veridant/veridant_buildings.obj')}
    for p in imports:
        if 'Assets/'+p not in pieces:unrelated['Assets/'+p]=sha(ROOT/'Assets'/p)
    files={};details=[]

    def record(relative):
        source=ROOT/relative;target=stage/relative
        before=sha(source) if source.exists() else None;backup=stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,backup)
            assert sha(backup)==before
        files[relative]={'before':before,'after':sha(target),'source':target.relative_to(ROOT).as_posix(),
                         'backup':backup.relative_to(ROOT).as_posix() if before else None}

    material='Assets/materials/veridant/backbar-v2';B.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()):record(p.relative_to(stage).as_posix())
    for i,spec in enumerate(specs):
        model=K.Model();detail=B.build_into(model,**spec)
        assert not model.boxes and not model.hulls
        for paint,rows in model.polygons.items():
            for index,(points,normal) in enumerate(rows):
                assert np.isfinite(points).all() and np.isfinite(normal).all()
                smooth=model.polygon_normals.get((paint,index))
                if smooth is not None:assert np.isfinite(smooth).all()
        points=np.vstack([p for rows in model.polygons.values() for p,n in rows])
        assert points[:,1].min()>=spec['lo'][1]-1e-6 and points[:,1].max()<=spec['hi'][1]+1e-6
        assert points[:,0].min()>=spec['lo'][0]-1e-6
        assert points[:,0].max()<=spec['hi'][0]+1.0
        assert model.triangle_count()<80000
        target=stage/pieces[i];target.parent.mkdir(parents=True,exist_ok=True)
        K.write_obj(target,model,'veridant_backbar');record(pieces[i]);record(str(Path(pieces[i]).with_suffix('.mtl')).replace('\\','/'))
        details.append({**spec,**detail,'triangles':model.triangle_count()})
        print(json.dumps(details[-1]),flush=True)
    # Only bindings owned by this display change; render and physics nodes stay
    # exactly as they were. In particular this is not another extraction from
    # the shared base OBJ, which already has the old cuboids removed.
    ia,ib=span(raw,'_class = "MaterialGroupList"');remaps=raw[ia:ib]
    remaps=re.sub(r'\{\s*from = "vr_backbar_[^"]+"\s+to = "[^"]+"\s*\}\s*,?\s*','',remaps)
    insertion=remaps.index('[',remaps.index('remaps ='))+1
    own=''.join(f'\n{{ from = "{paint}.vmat" to = "{resource}" }},' for paint,resource in B.MATERIALS.items())
    remaps=remaps[:insertion]+own+'\n'+remaps[insertion:]
    updated=raw[:ia]+remaps+raw[ib:]
    assert raw[a:b] in updated
    marker='_class = "PhysicsShapeList"';assert raw[raw.index(marker):]==updated[updated.index(marker):]
    target=stage/document;target.write_text(updated);record(document)
    assert units()==specs
    manifest={'revision':'veridant-backbar-v2','stage':args.stage,'files':files,'source_sha256':sources,
        'protected_sha256':protected,'unrelated_import_snapshot_sha256':unrelated,'required_source_snippets':snippets,
        'sections':details,'sections_replaced':3,'bottles':sum(d['bottles'] for d in details),
        'glasses':sum(d['glasses'] for d in details),'triangles':sum(d['triangles'] for d in details),
        'physics_bytes_exact':True,'render_imports_exact':True,'unrelated_obj_bytes_exact':True,
        'doorway_spans_preserved':True,'material_count':len(B.MATERIALS),
        'lighting_recipe':[s for spec in specs for s in B.lighting_specs(**spec)],
        'generated_albedo_archived':True,'runtime_walnut_texture_size':[2048,2048]}
    for group in (sources,protected):
        for p,h in group.items():assert sha(ROOT/p)==h,('Shared input changed',p)
    for p,item in files.items():
        assert sha(ROOT/item['source'])==item['after']
        assert (sha(ROOT/p) if (ROOT/p).exists() else None)==item['before'],('Shared target changed',p)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({k:manifest[k] for k in ('bottles','glasses','triangles','material_count')}),flush=True)


if __name__=='__main__':main()
