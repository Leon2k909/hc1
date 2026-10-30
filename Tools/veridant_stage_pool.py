"""Publish just the existing courtyard pool, preserving every unrelated OBJ byte."""
import argparse
import importlib.util
import inspect
import json
from pathlib import Path
import re
import shutil

import numpy as np
import map_kit as K
import veridant_map as V
import veridant_parts as P
import veridant_pool_detail as Detail
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/veridant/pool-v2'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args(); assert re.fullmatch('stage-[a-z0-9-]+',args.stage)
    stage = OUT/args.stage; stage.mkdir(parents=True,exist_ok=False)
    source_paths = ('Tools/veridant_pool_detail.py','Tools/veridant_stage_pool.py',
                    'Tools/map_kit.py','Tools/riverdale_parts.py','Tools/railhead_stage_extinguisher.py',
                    'Sources/Veridant/pool-v2/previous-pool.py','Sources/Veridant/pool-v2/water.shader')
    sources = {p:Patch.sha(ROOT/p) for p in source_paths}
    snippets = {'Tools/veridant_map.py':[inspect.getsource(V.pool),
                    'if paint.startswith( "vr_pool_" ) and paint in model.material_overrides:'],
                'Tools/veridant_materials.py':['from veridant_pool_detail import water_material',
                    'write_text( out / "vr_pool.vmat", water_material() )']}
    spec = importlib.util.spec_from_file_location('old_pool',ROOT/'Sources/Veridant/pool-v2/previous-pool.py')
    legacy = importlib.util.module_from_spec(spec); spec.loader.exec_module(legacy)
    old,old_water,new,new_water = K.Model(),K.Model(),K.Model(),K.Model()
    lights = list(P.LIGHTS)
    try:
        legacy.pool(old,old_water); old_lights = list(P.LIGHTS[len(lights):]); P.LIGHTS[:] = lights
        details = V.pool(new,new_water); new_lights = list(P.LIGHTS[len(lights):])
    finally: P.LIGHTS[:] = lights
    assert old_lights == new_lights
    assert len(old.boxes) == len(new.boxes) and len(old.hulls) == len(new.hulls)
    for before,after in zip(old.boxes,new.boxes):
        assert before[3] == after[3]
        for a,b in zip(before[:3],after[:3]): assert np.allclose(a,b,rtol=0,atol=1e-9)
    for before,after in zip(old.hulls,new.hulls):
        assert before[1] == after[1] and np.array_equal(before[0],after[0])
    assert old_water.polygons.keys() == new_water.polygons.keys()
    for a,b in zip(old_water.polygons['vr_pool'],new_water.polygons['vr_pool']):
        assert np.array_equal(a[0],b[0]) and np.array_equal(a[1],b[1])
    assert new.triangle_count() < 40000
    for paint,items in new.polygons.items():
        for points,normal in items: assert np.isfinite(points).all() and np.isfinite(normal).all()
    document = Path('Assets/models/maps/veridant/veridant_dress.vmdl')
    raw = (ROOT/document).read_text(); a,b = span(raw,'_class = "RenderMeshList"'); render = raw[a:b]
    installed = 'pool-v2/' in render
    imports = re.findall(r'filename\s*=\s*"([^"]+\.obj)"',render)
    base = Path('Assets')/next(p for p in imports if p.endswith('-base.obj'))
    protected = {p:Patch.sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
                  'Assets/models/maps/veridant/veridant_dress.obj','Assets/models/maps/veridant/veridant_water.vmdl',
                  'Assets/models/maps/veridant/veridant_water.obj','Assets/shaders/hc1_lowtide_water.shader',
                  'Assets/materials/veridant/vr_sea.vmat',
                  'Assets/models/maps/veridant/veridant_dress_hulls_default.obj',
                  'Assets/models/maps/veridant/veridant_dress_hulls_metal.obj')}
    for p in imports:
        if 'Assets/'+p != base.as_posix() and not p.startswith('models/maps/veridant/pool-v2/'):
            protected['Assets/'+p] = Patch.sha(ROOT/'Assets'/p)
    files = {}
    def record(relative):
        relative = Path(relative); target = ROOT/relative; source = stage/relative
        before = Patch.sha(target) if target.exists() else None
        backup = stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(target,backup)
            assert Patch.sha(backup) == before
        files[relative.as_posix()] = {'before':before,'after':Patch.sha(source),
            'source':source.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    material = Path('Assets/materials/veridant/pool-v2'); Detail.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()): record(p.relative_to(stage))
    water = Path('Assets/materials/veridant/vr_pool.vmat')
    (stage/water).write_text(Detail.water_material()); record(water)
    shader = Path('Assets/shaders/hc1_veridant_pool_v2.shader')
    (stage/shader).parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(ROOT/'Sources/Veridant/pool-v2/water.shader',stage/shader);record(shader)
    leaf = Path('Assets/models/maps/veridant/pool-v2/pool.obj')
    (stage/leaf).parent.mkdir(parents=True,exist_ok=True)
    V.configure(new); K.write_obj(stage/leaf,new,'veridant_pool_v2'); record(leaf);record(leaf.with_suffix('.mtl'))
    if installed:
        protected[base.as_posix()] = Patch.sha(ROOT/base)
        protected[document.as_posix()] = Patch.sha(ROOT/document)
        result = {'removed_triangles':0,'unrelated_obj_bytes_exact':True}
    else:
        lookup,polygons = Patch.lookup_polygons(old)
        result,found = Patch.replace_obj(ROOT/base,stage/'proof/combined.obj',stage/base,lookup,stage/leaf)
        Patch.coverage(found,lookup,polygons); assert result['removed_triangles'] == old.triangle_count()
        record(base)
    x,y = span(render,'_class = "RenderMeshFile"'); node = render[x:y]
    node = re.sub(r'name = "[^"]+"','name = "veridant_pool_v2"',node,count=1)
    node = re.sub(r'filename = "[^"]+"',f'filename = "{leaf.relative_to("Assets").as_posix()}"',node,count=1)
    at = render.rfind(']'); prefix = render[:at].rstrip()
    replacement = prefix+('' if prefix.endswith(',') else ',')+'\n'+node+'\n'+render[at:]
    updated = raw[:a]+replacement+raw[b:]
    remaps = ''.join(f'{{ from = "{paint}.vmat" to = "{resource}" }},\n' for paint,resource in Detail.MATERIALS.items())
    at = updated.index('[',updated.index('remaps ='))+1; updated = updated[:at]+'\n'+remaps+updated[at:]
    marker = '_class = "PhysicsShapeList"'
    assert raw[raw.index(marker):] == updated[updated.index(marker):]
    if not installed:
        (stage/document).write_text(updated); record(document)
    manifest = {'revision':'veridant-pool-v2','stage':args.stage,'files':files,
                'source_sha256':sources,'required_source_snippets':snippets,'protected_sha256':protected,
                'base_import':base.as_posix(),'details':details,'old_triangles':old.triangle_count(),
                'new_triangles':new.triangle_count(),'physics_bytes_exact':True,
                'collision_exact':True,'water_plane_exact':True,'lights_exact':True,**result}
    (stage/'plan-draft.json').write_text(json.dumps(manifest,indent=2)+'\n')
    for group in (sources,protected):
        for p,h in group.items(): assert Patch.sha(ROOT/p) == h,('Shared input changed',p)
    for p,item in files.items():
        assert Patch.sha(ROOT/item['source']) == item['after']
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None) == item['before'],('Shared target changed',p)
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'stage':args.stage,'old_triangles':manifest['old_triangles'],
        'new_triangles':manifest['new_triangles'],'files':len(files),'collision_exact':True,'details':details}))


if __name__ == '__main__': main()
