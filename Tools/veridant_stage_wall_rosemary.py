"""Stage only the pictured retaining-wall plants; preserve all other foliage."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import shutil

import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_map as V
import veridant_wall_rosemary as R
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span
from veridant_stage_stone_pine import parsed, face_keys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/veridant/shrub-volume-v1'
RESOURCE = Path('Assets/models/maps/veridant/shrub-volume-v1')
DOCUMENT = Path('Assets/models/maps/veridant/veridant_foliage.vmdl')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args(); assert re.fullmatch('stage-[a-z0-9-]+', args.stage)
    stage = OUT/args.stage; assert not stage.exists(); stage.mkdir(parents=True)
    source_paths = ('Tools/veridant_wall_rosemary.py', 'Tools/veridant_stage_wall_rosemary.py',
                    'Tools/map_kit.py', 'Tools/riverdale_parts.py',
                    'Sources/Veridant/planter-shrub-v1/beech-source.json',
                    'Sources/Veridant/shrub-volume-v1/previous-shrubs.py.txt')
    sources = {p: Patch.sha(ROOT/p) for p in source_paths}
    snippets = {'Tools/veridant_map.py': [
        'if paint.startswith( "vr_wall_herb_" ) and paint in model.material_overrides:',
        'from veridant_wall_rosemary import build_into as wall_rosemary',
        'wall_rosemary( foliage, ( 740.0, 34.0 ), ( 753.0, 148.0 ), 0.0,\n'
        '                   seed=812, kind="rosemary", h=25.0, count=10 )']}
    raw = (ROOT/DOCUMENT).read_text()
    a, b = span(raw, '_class = "RenderMeshList"'); render = raw[a:b]
    imports = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', render)
    existing = 'shrub-volume-v1/' in render
    base = Path('Assets')/next(p for p in imports if p.endswith('foliage-base.obj'))
    protected = {p: Patch.sha(ROOT/p) for p in ('Assets/scenes/maps/Veridant/veridant.scene',
        'Assets/models/maps/veridant/veridant_foliage.obj')}
    for p in imports:
        if 'shrub-volume-v1/' not in p and ('Assets/'+p != base.as_posix() or existing):
            protected['Assets/'+p] = Patch.sha(ROOT/'Assets'/p)
    files = {}
    def record(relative):
        source = ROOT/relative; target = stage/relative
        before = Patch.sha(source) if source.exists() else None
        backup = stage/'before'/relative
        if before:
            backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(source, backup)
            assert Patch.sha(backup) == before
        files[relative.as_posix()] = {'before': before, 'after': Patch.sha(target),
            'source': target.relative_to(ROOT).as_posix(),
            'backup': backup.relative_to(ROOT).as_posix() if before else None}
    material = Path('Assets/materials/veridant/shrub-volume-v1')
    R.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()): record(p.relative_to(stage))
    pieces = []; statistics = []
    for section in range(2):
        model = K.Model(); stats = R.build_into(model, section=section)
        assert not model.boxes and not model.hulls and not model.props
        assert model.triangle_count() < 65000
        for paint, rows in model.polygons.items():
            for i, (points, normal) in enumerate(rows):
                assert np.isfinite(points).all() and np.isfinite(normal).all()
                ns = model.polygon_normals.get((paint, i))
                if ns is not None: assert np.isfinite(ns).all()
        points = np.vstack([p for rows in model.polygons.values() for p, n in rows])
        assert points[:,0].min() > 732 and points[:,0].max() < 761.8
        assert points[:,1].min() > 62 and points[:,1].max() < 153
        assert points[:,2].min() >= -.6 and points[:,2].max() < 27
        V.configure(model)
        assert all(model.material_overrides[p] == R.MATERIALS[p] for p in model.polygons)
        relative = RESOURCE/f'rosemary-{section}.obj'
        (stage/relative).parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(stage/relative, model, 'veridant_wall_rosemary')
        record(relative); record(relative.with_suffix('.mtl')); pieces.append(relative)
        stats.update(triangles=model.triangle_count(), bounds=[points.min(0).tolist(), points.max(0).tolist()])
        statistics.append(stats); print(json.dumps(stats), flush=True)
    removal = {'removed_triangles': 0, 'unrelated_obj_bytes_exact': True}
    updated = raw
    if not existing:
        namespace = dict(vars(P))
        exec((ROOT/'Sources/Veridant/shrub-volume-v1/previous-shrubs.py.txt').read_text(), namespace)
        old = K.Model()
        namespace['shrubs'](old, (740., 34.), (753., 148.), 0., seed=812, kind='rosemary', h=25., count=10)
        assert old.triangle_count() == 80
        V.configure(old)
        K.write_obj(stage/'old-wall-shrubs.obj', old, 'veridant_foliage')
        old_lines, old_vertices, _ = parsed((stage/'old-wall-shrubs.obj').read_text())
        wanted = Counter(key for _, key in face_keys(old_lines, old_vertices))
        source_bytes = (ROOT/base).read_bytes()
        lines, vertices, counts = parsed(source_bytes.decode())
        observed = Counter(); removed = set()
        for index, key in face_keys(lines, vertices):
            if key in wanted: observed[key] += 1; removed.add(index)
        assert observed == wanted, ('Legacy geometry mismatch', sum(wanted.values()), sum(observed.values()))
        assert len(removed) == 80
        retained = ''.join(line for i, line in enumerate(lines) if i not in removed).encode()
        (stage/base).parent.mkdir(parents=True, exist_ok=True); (stage/base).write_bytes(retained)
        assert [sum(line.startswith(p) for i, line in enumerate(lines) if i not in removed)
                for p in ('v ', 'vt ', 'vn ')] == counts
        removal = {'removed_triangles': len(removed), 'unrelated_obj_bytes_exact': True,
                   'retained_bytes_sha256': Patch.sha(stage/base)}
        record(base)
        i, j = span(render, '_class = "RenderMeshFile"'); template = render[i:j]; nodes = []
        for piece in pieces:
            node_name = 'wall_'+piece.stem.replace('-', '_')
            node = re.sub(r'name = "[^"]+"', f'name = "{node_name}"', template, count=1)
            node = re.sub(r'filename = "[^"]+"', f'filename = "{piece.relative_to("Assets").as_posix()}"', node, count=1)
            nodes.append(node)
        end = render.rfind(']'); prefix = render[:end].rstrip()
        new_render = prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(nodes)+'\n'+render[end:]
        updated = raw[:a]+new_render+raw[b:]
        remaps = ''.join(f'{{ from = "{p}.vmat" to = "{r}" }},\n' for p, r in R.MATERIALS.items())
        at = updated.index('[', updated.index('remaps ='))+1
        updated = updated[:at]+'\n'+remaps+updated[at:]
        assert 'PhysicsShapeList' not in raw and 'PhysicsShapeList' not in updated
        (stage/DOCUMENT).parent.mkdir(parents=True, exist_ok=True); (stage/DOCUMENT).write_text(updated)
        record(DOCUMENT)
    else:
        assert all(p.relative_to('Assets').as_posix() in render for p in pieces)
        updated = raw.replace('name = "wall_rosemary-0"', 'name = "wall_rosemary_0"')
        updated = updated.replace('name = "wall_rosemary-1"', 'name = "wall_rosemary_1"')
        for paint, resource in R.MATERIALS.items():
            pattern = r'(from\s*=\s*"'+re.escape(paint)+r'\.vmat"\s+to\s*=\s*")[^"]+("\s*})'
            updated, matches = re.subn(pattern, lambda m:m[1]+resource+m[2], updated)
            assert matches == 1
        if updated != raw:
            (stage/DOCUMENT).parent.mkdir(parents=True, exist_ok=True)
            (stage/DOCUMENT).write_text(updated); record(DOCUMENT)
        else:
            protected[DOCUMENT.as_posix()] = Patch.sha(ROOT/DOCUMENT)
    manifest = {'revision': 'veridant-shrub-volume-v1', 'stage': args.stage, 'files': files,
        'source_sha256': sources, 'protected_sha256': protected, 'required_source_snippets': snippets,
        'first_install': not existing, 'base_import': base.as_posix(), 'statistics': statistics, **removal,
        'plants_changed': 10, 'root_clumps': sum(s['root_clumps'] for s in statistics),
        'leaf_pairs': sum(s['leaf_pairs'] for s in statistics),
        'new_triangles': sum(s['triangles'] for s in statistics),
        'scene_unchanged': True, 'collision_unchanged': True, 'original_obj_indices_preserved': True}
    for group in (sources, protected):
        for p, h in group.items(): assert Patch.sha(ROOT/p) == h, ('Shared input changed', p)
    for p, item in files.items():
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None) == item['before'], ('Shared target changed', p)
    for p, parts in snippets.items(): assert all(s in (ROOT/p).read_text() for s in parts)
    (stage/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage': args.stage})+'\n')
    print(json.dumps({'files': len(files), 'triangles': manifest['new_triangles'], **removal}), flush=True)


if __name__ == '__main__': main()
