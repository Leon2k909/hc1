"""Stage additive casement imports; publish through the open editor separately."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil

import numpy as np

import map_kit as K
import building_textures as BT
import belltower_map as B
import belltower_open_windows as W
from belltower_safe_imports import span

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/open-windows-v1'


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def openings(name):
    """Use the real building prefix, stopping before dressing or furnishing it."""
    tree = ast.parse((ROOT/'Tools/belltower_map.py').read_text())
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    stop = next(i for i, n in enumerate(fn.body) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'style' for t in n.targets))
    scope = dict(B.__dict__, model=K.Model(), lights=[], rng=np.random.default_rng(7))
    exec(compile(ast.Module(body=fn.body[:stop+1], type_ignores=[]), '<building-prefix>', 'exec'), scope)
    return [(face, wall, o, scope['style']['trim'], face in scope['style'].get('covered_windows', ()))
            for face, wall in scope['walls'].items() for o in wall.openings if o.kind == 'window']


def check(model):
    assert not model.boxes and not model.hulls and not model.props
    triangles = 0
    min_area = float('inf')
    for paint, faces in model.polygons.items():
        for points, normal in faces:
            assert np.all(np.isfinite(points)) and np.all(np.isfinite(normal))
            # Match map_kit's export precision and fan triangulation exactly.
            pts = np.round(np.array(points), 3)
            for j in range(1, len(pts)-1):
                cross = np.cross(pts[j]-pts[0], pts[j+1]-pts[0])
                area = np.linalg.norm(cross)/2
                assert area > 1e-7, (paint, area)
                assert np.dot(cross, normal) > 0, (paint, 'reversed face')
                triangles += 1
                min_area = min(min_area, area)
    return dict(triangles=triangles, minimum_triangle_area=min_area, collision_shapes=0)


def updated_vmdl(text, part, model):
    start, end = span(text, '_class = "RenderMeshList"')
    if 'open-windows-v1' in text:
        assert text.count(f'models/maps/belltower/open-windows-v1/{part}/windows.obj') == 1
        for paint in model.polygons:
            assert re.search(r'from\s*=\s*"'+re.escape(paint)+r'\.vmat"', text)
        return text
    anchor = re.search(r'children\s*=\s*\[', text[start:end])
    assert anchor
    insert = start+anchor.end()
    node = f'''
{{
    _class = "RenderMeshFile"
    name = "open_casements_{part}"
    filename = "models/maps/belltower/open-windows-v1/{part}/windows.obj"
    import_translation = [ 0.0, 0.0, 0.0 ]
    import_rotation = [ 0.0, 0.0, 0.0 ]
    import_scale = 1.0
    align_origin_x_type = "None"
    align_origin_y_type = "None"
    align_origin_z_type = "None"
    parent_bone = ""
    import_filter = {{ exclude_by_default = false exception_list = [ ] }}
}},
'''
    result = text[:insert]+node+text[insert:]
    anchor = re.search(r'remaps\s*=\s*\[', result)
    additions = ''
    for paint in sorted(model.polygons):
        if re.search(r'from\s*=\s*"'+re.escape(paint)+r'\.vmat"', text):
            continue
        material = model.material_overrides[paint] if paint in model.material_overrides else BT.material_path(paint)
        assert (ROOT/'Assets'/material).is_file(), material
        additions += f'\n{{ from = "{paint}.vmat" to = "{material}" }},'
    result = result[:anchor.end()]+additions+result[anchor.end():]
    # Exact reconstruction establishes that nothing pre-existing was replaced.
    assert result.replace(node, '', 1).replace(additions, '', 1) == text
    assert re.findall(r'filename = "([^"]+)"', text) == [
        p for p in re.findall(r'filename = "([^"]+)"', result) if '/open-windows-v1/' not in p]
    a, b = span(text, '_class = "PhysicsShapeList"')
    c, d = span(result, '_class = "PhysicsShapeList"')
    assert text[a:b] == result[c:d]
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--revision', required=True)
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9-]+', args.revision)
    folder = OUT/args.revision/'stage'
    assert not folder.exists(), 'Use a fresh stage revision.'
    folder.mkdir(parents=True)
    models = dict(centre=K.Model(), west=K.Model())
    records = []
    for building, part in [('town_hall', 'centre'), ('bakery', 'west'), ('inn', 'west')]:
        for face, wall, opening, trim, covered in openings(building):
            leaves = W.build(models[part], wall, opening, trim, covered)
            for pose in leaves:
                # Past 90 degrees: the free edge retreats outside its own jamb.
                assert np.dot(pose['along'], pose['run'])*pose['handed'] < 0
                assert np.dot(pose['along'], pose['out']) > (.03 if covered else .8)
            records.append(dict(part=part, building=building, face=face, axis=wall.axis,
                                across=wall.across, r0=opening.r0, r1=opening.r1,
                                z0=opening.z0, z1=opening.z1, trim=trim, covered=covered, leaves=leaves))
    assert len(records) == 28
    models['east'] = models['west'].mirrored(B.EAST_PAINTS)
    manifest = dict(revision='open-windows-v1', stage_revision=args.revision, files={},
                    source_sha256={}, protected_sha256={}, windows=42, leaves=84,
                    openings=records, geometry={}, previous_imports_and_physics_preserved=True)
    for source in ['Tools/belltower_open_windows.py', 'Tools/belltower_stage_open_windows.py',
                   'Tools/belltower_map.py']:
        manifest['source_sha256'][source] = sha(ROOT/source)
    scene = 'Assets/scenes/maps/Belltower/belltower.scene'
    manifest['protected_sha256'][scene] = sha(ROOT/scene)
    for i in range(3):
        rel = f'Assets/materials/belltower/church-windows-v1/church_window_glass_{i}.vmat'
        manifest['protected_sha256'][rel] = sha(ROOT/rel)
    for part, model in models.items():
        manifest['geometry'][part] = check(model)
        resource = f'Assets/models/maps/belltower/open-windows-v1/{part}/windows.obj'
        target = folder/resource
        target.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(target, model, 'belltower_'+part)
        for file in [target, target.with_suffix('.mtl')]:
            relative = file.relative_to(folder).as_posix()
            existing = ROOT/relative
            backup = None
            before_hash = None
            if existing.exists():
                installed = json.loads((OUT/'review-d/stage/manifest.json').read_text())['files'][relative]
                assert sha(existing) == installed['after'], 'Private geometry changed outside this task: '+relative
                backup = folder/'backup'/relative
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(existing, backup)
                before_hash = sha(existing)
            manifest['files'][relative] = dict(source=file.relative_to(ROOT).as_posix(), before=before_hash,
                                              after=sha(file), backup=backup.relative_to(ROOT).as_posix() if backup else None)
        relative = f'Assets/models/maps/belltower/belltower_{part}.vmdl'
        before = ROOT/relative
        after = folder/relative
        after.parent.mkdir(parents=True, exist_ok=True)
        backup = folder/'backup'/relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(before, backup)
        after.write_bytes(updated_vmdl(before.read_bytes().decode('utf-8'), part, model).encode('utf-8'))
        manifest['files'][relative] = dict(source=after.relative_to(ROOT).as_posix(),
                                          before=sha(before), after=sha(after), backup=backup.relative_to(ROOT).as_posix())
    (folder/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'revision': args.revision})+'\n')
    print(json.dumps({k: manifest[k] for k in ['windows', 'leaves', 'geometry']}, indent=2))


if __name__ == '__main__':
    main()
