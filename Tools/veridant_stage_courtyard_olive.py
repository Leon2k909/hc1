"""Publish just the grand-stair planter, preserving other foliage and its indices."""
import argparse
from collections import Counter
import inspect
import json
from pathlib import Path
import re
import shutil
import numpy as np
import map_kit as K
import veridant_parts as P
import veridant_map as V
import veridant_courtyard_olive as O
import railhead_stage_extinguisher as Patch
from belltower_safe_imports import span
from veridant_stage_stone_pine import parsed, face_keys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/veridant/foliage-hero-v2'
RESOURCE = Path('Assets/models/maps/veridant/courtyard-olive-v2')
DOCUMENT = Path('Assets/models/maps/veridant/veridant_foliage.vmdl')


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--stage', required=True)
    args = parser.parse_args(); assert re.fullmatch('stage-[a-z0-9-]+', args.stage)
    stage = OUT/args.stage; assert not stage.exists(); stage.mkdir(parents=True)
    sources = {p: Patch.sha(ROOT/p) for p in ('Tools/veridant_courtyard_olive.py',
        'Tools/veridant_stage_courtyard_olive.py', 'Tools/map_kit.py', 'Tools/riverdale_parts.py',
        'Tools/railhead_stage_extinguisher.py', 'Sources/Veridant/foliage-hero-v2/previous-olive.py.txt',
        'Sources/Veridant/foliage-hero-v2/previous-shrubs.py.txt')}
    snippets = {'Tools/veridant_map.py': [inspect.getsource(V.courtyard),
        'if paint.startswith( "vr_courtyard_olive_" ) and paint in model.material_overrides:']}
    assert V.PLANTER == (220., 316., 202., 276.)
    raw = (ROOT/DOCUMENT).read_text(); a, b = span(raw, '_class = "RenderMeshList"'); render = raw[a:b]
    imports = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', render)
    existing = 'courtyard-olive-v2/' in render
    base = Path('Assets')/next(p for p in imports if p.endswith('foliage-base.obj'))
    # Asset publication never writes the scene. Other authorised work may save
    # that document while these independent render imports are being staged.
    protected = {p: Patch.sha(ROOT/p) for p in ('Assets/models/maps/veridant/veridant_foliage.obj',)}
    for p in imports:
        if 'courtyard-olive-v2/' not in p and ('Assets/'+p != base.as_posix() or existing):
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
    material = Path('Assets/materials/veridant/courtyard-olive-v2')
    O.write_materials(stage/material)
    for p in sorted((stage/material).iterdir()): record(p.relative_to(stage))
    pieces = []; statistics = {}
    for name, builder in (('planting', O.build_planting),):
        model = K.Model(); statistics[name] = builder(model)
        assert not model.boxes and not model.hulls
        assert model.triangle_count() < 80000
        for paint, rows in model.polygons.items():
            for i, (points, normal) in enumerate(rows):
                assert np.isfinite(points).all() and np.isfinite(normal).all()
                ns = model.polygon_normals.get((paint, i))
                if ns is not None: assert np.isfinite(ns).all()
        V.configure(model)
        assert all(model.material_overrides[p] == O.MATERIALS[p] for p in model.polygons)
        relative = RESOURCE/f'{name}.obj'; (stage/relative).parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(stage/relative, model, 'veridant_courtyard_olive')
        record(relative); record(relative.with_suffix('.mtl')); pieces.append(relative)
        statistics[name]['triangles'] = model.triangle_count()
        print(json.dumps({name: statistics[name]}), flush=True)
    removal = {'removed_triangles': 0, 'unrelated_obj_bytes_exact': True}
    updated = raw
    if not existing:
        namespace = dict(vars(P))
        for p in ('previous-olive.py.txt', 'previous-shrubs.py.txt'):
            exec((ROOT/'Sources/Veridant/foliage-hero-v2'/p).read_text(), namespace)
        old = K.Model()
        namespace['olive'](old, (272., 239., 42.), 180, seed=11, spread=1., cards=15, leaf_scale=.72)
        namespace['shrubs'](old, (228., 210.), (308., 268.), 42., seed=12, kind='shrub', h=20.)
        V.configure(old)
        assert not old.boxes and not old.hulls
        # Leaf cards have coincident, oppositely wound fronts and backs.
        # Match oriented triangles and their multiplicities, preserving both.
        K.write_obj(stage/'old-planter.obj', old, 'veridant_foliage')
        old_lines, old_vertices, _ = parsed((stage/'old-planter.obj').read_text())
        wanted = Counter(key for _, key in face_keys(old_lines, old_vertices))
        source_bytes = (ROOT/base).read_bytes()
        lines, vertices, counts = parsed(source_bytes.decode())
        observed = Counter(); removed = set()
        for index, key in face_keys(lines, vertices):
            if key in wanted: observed[key] += 1; removed.add(index)
        assert observed == wanted, ('Legacy geometry does not match', sum(wanted.values()), sum(observed.values()))
        retained = ''.join(line for i, line in enumerate(lines) if i not in removed).encode()
        (stage/base).parent.mkdir(parents=True, exist_ok=True); (stage/base).write_bytes(retained)
        assert len(removed) == old.triangle_count()
        assert [sum(line.startswith(p) for i, line in enumerate(lines) if i not in removed)
                for p in ('v ', 'vt ', 'vn ')] == counts
        removal = {'removed_triangles': len(removed), 'unrelated_obj_bytes_exact': True,
                   'retained_bytes_sha256': Patch.sha(stage/base)}
        record(base)
        i, j = span(render, '_class = "RenderMeshFile"'); template = render[i:j]; nodes = []
        for piece in pieces:
            node = re.sub(r'name = "[^"]+"', f'name = "courtyard_olive_{piece.stem}"', template, count=1)
            node = re.sub(r'filename = "[^"]+"', f'filename = "{piece.relative_to("Assets").as_posix()}"', node, count=1)
            nodes.append(node)
        end = render.rfind(']'); prefix = render[:end].rstrip()
        new_render = prefix+('' if prefix.endswith(',') else ',')+'\n'+',\n'.join(nodes)+'\n'+render[end:]
        updated = raw[:a]+new_render+raw[b:]
        remaps = ''.join(f'{{ from = "{p}.vmat" to = "{r}" }},\n' for p, r in O.MATERIALS.items())
        at = updated.index('[', updated.index('remaps ='))+1
        updated = updated[:at]+'\n'+remaps+updated[at:]
        assert 'PhysicsShapeList' not in raw and 'PhysicsShapeList' not in updated
        (stage/DOCUMENT).parent.mkdir(parents=True, exist_ok=True); (stage/DOCUMENT).write_text(updated)
        record(DOCUMENT)
    else:
        assert all(p.relative_to('Assets').as_posix() in render for p in pieces)
        name_at = render.index('name = "courtyard_olive_tree"') if 'name = "courtyard_olive_tree"' in render else -1
        if name_at >= 0:
            marker_at = render.rfind('_class = "RenderMeshFile"', 0, name_at)
            node_at = render.rfind('{', 0, marker_at)
            start, end = span(render[node_at:], '_class = "RenderMeshFile"')
            start += node_at; end += node_at
            if render[end:].lstrip().startswith(','):
                end += render[end:].index(',')+1
            elif render[:start].rstrip().endswith(','):
                start = render[:start].rfind(',')
            new_render = render[:start]+render[end:]
            updated = raw[:a]+new_render+raw[b:]
            (stage/DOCUMENT).parent.mkdir(parents=True, exist_ok=True); (stage/DOCUMENT).write_text(updated)
            record(DOCUMENT)
        # Drop only the unused materials from the discarded procedural tree.
        cleaned = updated
        for name in ('bark', 'leaf', 'leaf_light', 'leaf_back'):
            cleaned = re.sub(r'\{ from = "vr_courtyard_olive_'+name+r'\.vmat" to = "[^"]+" \},?\s*', '', cleaned)
        if cleaned != raw:
            updated = cleaned
            (stage/DOCUMENT).parent.mkdir(parents=True, exist_ok=True); (stage/DOCUMENT).write_text(updated)
            if DOCUMENT.as_posix() not in files: record(DOCUMENT)
            else: files[DOCUMENT.as_posix()]['after'] = Patch.sha(stage/DOCUMENT)
        elif DOCUMENT.as_posix() not in files: protected[DOCUMENT.as_posix()] = Patch.sha(ROOT/DOCUMENT)
    manifest = {'revision': 'veridant-courtyard-olive-v2', 'stage': args.stage, 'files': files,
        'source_sha256': sources, 'protected_sha256': protected, 'required_source_snippets': snippets,
        'first_install': not existing, 'base_import': base.as_posix(), 'statistics': statistics, **removal,
        'plants_changed': 1, 'planter_bounds': list(V.PLANTER), 'base_plan': [272., 239., 42.],
        'scene_unchanged': True, 'collision_unchanged': True, 'original_obj_indices_preserved': True}
    manifest['native_tree'] = O.build_tree(None)
    for group in (sources, protected):
        for p, h in group.items(): assert Patch.sha(ROOT/p) == h, ('Shared input changed', p)
    for p, item in files.items():
        assert (Patch.sha(ROOT/p) if (ROOT/p).exists() else None) == item['before'], ('Shared target changed', p)
    for p, parts in snippets.items(): assert all(s in (ROOT/p).read_text() for s in parts)
    (stage/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage': args.stage})+'\n')
    print(json.dumps({'files': len(files), 'statistics': statistics, **removal}), flush=True)


if __name__ == '__main__': main()
