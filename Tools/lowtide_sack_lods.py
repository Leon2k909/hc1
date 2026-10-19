"""Offline distance-detail candidates for sewn sacks; no native LOD assignment.

Retains the reviewed close mesh. Reduced bodies use the same deformation and
cloth coordinates; fine mouth stitching merges into a hem, then disappears
below a useful screen size. The large dressing/fleet aggregates still require
native profiling and an appropriate grouping strategy before any switching.
"""
import argparse
import json
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_sack_construction as S

REVISION = 'sewn-sack-distance-candidates-v5'
BASE = K.ROOT/'output/lowtide/quality-pass/sack-construction'
LEVELS = {
    1: dict(sides=24, rings=[-1, -.96, -.89, -.80, -.66, -.48, -.24, 0, .24, .48, .66, .80, .89, .96, 1],
            angles=[0, 1, 2, 4, 6, 8, 10, 12, 14, 16, 18, 19, 20, 21, 22, 24, 26, 28, 30, 32, 34, 36, 38, 39, 40], seams='simplified_closed_seams'),
    2: dict(sides=16, rings=[-1, -.96, -.80, -.48, 0, .48, .80, .96, 1],
            angles=[0, 1, 4, 7, 10, 13, 16, 19, 20, 21, 24, 27, 30, 33, 36, 39, 40], seams='body_only'),
}


def sack(model, lo, size, level, *, seed=None):
    if level == 0: return S.sack(model, lo, size, seed=seed)
    params = LEVELS[level]
    reference = K.Model()
    full = S.sack(reference, lo, size, seed=seed)
    # All reduced vertices are a subset of the reviewed body. Re-evaluating a
    # coarser perimeter would change cloth UVs, bound normalization and shading.
    rows = [int(np.flatnonzero(np.isclose(S.RINGS, value))[0]) for value in params['rings']]
    angles = np.array(params['angles'])
    assert len(angles) == params['sides']+1
    def attribute(polygon, vertex):
        points, normal = reference.polygons[S.PAINT][polygon]
        normals = reference.polygon_normals.get((S.PAINT, polygon), [normal]*len(points))
        return points[vertex], reference.polygon_uvs[(S.PAINT, polygon)][vertex], normals[vertex]
    def ring(row, angle):
        if row == len(S.RINGS)-1:
            polygon = 2*((row-1)*S.SIDES + min(angle, S.SIDES-1))
            return attribute(polygon, 2 if angle == S.SIDES else 1)
        if angle == S.SIDES:
            return attribute(2*(row*S.SIDES + S.SIDES-1)+1, 2)
        return attribute(2*(row*S.SIDES+angle), 0)
    def triangle(attrs):
        points, uv, normals = zip(*attrs)
        model.polygon(S.PAINT, points, uv=uv, normals=normals)
    for a, b in zip(rows, rows[1:]):
        for i, j in zip(angles, angles[1:]):
            ai, bi, bj, aj = ring(a, i), ring(b, i), ring(b, j), ring(a, j)
            triangle((ai, bi, bj))
            triangle((ai, bj, aj))
    cap_start = 2*(len(S.RINGS)-1)*S.SIDES
    for end in (0, 1):
        start = cap_start + end*S.SIDES
        centre = attribute(start, 2 if end else 0)
        def cap(angle):
            if angle == S.SIDES: return attribute(start+S.SIDES-1, 0 if end else 2)
            return attribute(start+angle, 1)
        for i, j in zip(angles, angles[1:]):
            triangle((cap(j), cap(i), centre) if end else (centre, cap(i), cap(j)))
    count = 2*len(rows)*params['sides']
    if level == 1:
        # A seam can still be a visible line after its cross-section becomes
        # subpixel. Retain coarse closed shells rather than removing the cue.
        def reduced_tube(start, ring_count, side_count, selected):
            def vertex(row, angle):
                if row == ring_count-1:
                    return attribute(start+(row-1)*side_count+min(angle, side_count-1), 2 if angle==side_count else 3)
                return attribute(start+row*side_count+min(angle, side_count-1), 1 if angle==side_count else 0)
            for a, b in zip(selected, selected[1:]):
                for j in range(side_count):
                    points = (vertex(a,j), vertex(a,j+1), vertex(b,j+1), vertex(b,j))
                    triangle((points[0], points[1], points[2]))
                    triangle((points[0], points[2], points[3]))
            for cap in range(2):
                polygon = start+(ring_count-1)*side_count+cap
                length = len(reference.polygons[S.PAINT][polygon][0])
                for k in range(1, length-1): triangle((attribute(polygon,0), attribute(polygon,k), attribute(polygon,k+1)))
            return 2*(len(selected)-1)*side_count+2*(side_count-2)
        side_start = full['body_triangles']
        count += reduced_tube(side_start, len(S.RINGS), 4, list(range(0, len(S.RINGS), 2)))
        mouth_start = side_start+(len(S.RINGS)-1)*4+2
        count += reduced_tube(mouth_start, 43, 3, [0, 8, 16, 24, 32, 40, 42])
    model.tile_overrides[S.PAINT] = S.TILE
    return dict(body_triangles=2*len(rows)*params['sides'],
                total_triangles=count, seed=full['seed'])


def generate(out, baseline=BASE, reuse_components=None):
    out = Path(out).resolve()
    assert out.is_relative_to(K.ROOT/'output/lowtide/quality-pass'), 'Offline candidates only'
    baseline = Path(baseline).resolve()
    assert baseline.is_relative_to(K.ROOT/'output/lowtide/quality-pass')
    out.mkdir(parents=True, exist_ok=True)
    base_path = baseline/'manifest.json'
    base = json.loads(base_path.read_text())
    assert all(S.sha(K.ROOT/p) == h for p, h in base['sources'].items())
    assert all(S.sha(K.ROOT/p) == h for p, h in base['protected'].items())
    reused = None
    if reuse_components is not None:
        reuse_components = Path(reuse_components).resolve()
        assert reuse_components.is_relative_to(K.ROOT/'output/lowtide/quality-pass')
        assert not (out/'manifest.json').exists(), 'Reuse into a new folder; preserve reviewed evidence'
        reused = json.loads(reuse_components.read_text())
        assert reused['revision'] == REVISION and reused['parameters'] == {str(k):v for k,v in LEVELS.items()}
        previous_base = json.loads((K.ROOT/reused['baseline_manifest']).read_text())
        assert previous_base['layout'] == base['layout'], 'Reviewed components belong to a different layout'
        assert all(v['component_sha256'] == previous_base['models'][n]['component_sha256'] for n,v in base['models'].items())
    manifest = dict(revision=REVISION, project_root=str(K.ROOT), native_switching_configured=False, production_changed=False,
        baseline_manifest_sha256=S.sha(base_path), baseline_manifest=base_path.relative_to(K.ROOT).as_posix(),
        parameters=LEVELS, levels={}, protected=base['protected'], material_libraries={},
        sources={str(Path(p).relative_to(K.ROOT).as_posix()): S.sha(p) for p in (__file__, S.__file__, K.__file__)})
    if reused:
        manifest['reused_components_manifest'] = reuse_components.relative_to(K.ROOT).as_posix()
        manifest['reused_components_manifest_sha256'] = S.sha(reuse_components)
    for level in LEVELS:
        target_dir = out/f'level-{level}'
        target_dir.mkdir(exist_ok=True)
        manifest['levels'][level] = {}
        for name, rows in base['layout'].items():
            component = target_dir/f'{name}-sacks.obj'
            if reused:
                old = reused['levels'][str(level)][name]
                source = (K.ROOT/old['component']).resolve()
                assert source.is_relative_to(K.ROOT/'output/lowtide/quality-pass')
                assert old['sacks'] == len(rows) and S.sha(source) == old['component_sha256']
                component.write_bytes(source.read_bytes())
                component.with_suffix('.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
                counts = [old['per_sack_triangles']]*len(rows)
                assert sum(counts) == old['triangles']
            else:
                model = K.Model()
                counts = [sack(model, row['lo'], row['size'], level)['total_triangles'] for row in rows]
                K.write_obj(component, model, name)
            before = baseline/'before'/f'{name}.obj'
            assert S.sha(before) == base['changes'][f'models/maps/lowtide/{name}.obj']['before']
            updated, removed = S.replace(before.read_text(), component.read_text())
            assert removed == base['models'][name]['old_triangles']
            staged = target_dir/'stage/models/maps/lowtide/lod-candidates'/f'{name}_sack_lod{level}.obj'
            staged.parent.mkdir(parents=True, exist_ok=True)
            staged.write_bytes(updated.encode())
            libraries = [line.split(maxsplit=1)[1] for line in updated.splitlines() if line.startswith('mtllib ')]
            assert len(libraries) == 1 and Path(libraries[0]).name == libraries[0]
            library = K.ASSETS/'models/maps/lowtide'/libraries[0]
            relative = library.relative_to(K.ROOT).as_posix()
            assert S.sha(library) == base['protected'][relative]
            staged_library = staged.parent/library.name
            staged_library.write_bytes(library.read_bytes())
            manifest['material_libraries'][staged_library.relative_to(K.ROOT).as_posix()] = dict(source=relative, sha256=S.sha(library))
            manifest['levels'][level][name] = dict(sacks=len(rows), triangles=sum(counts),
                per_sack_triangles=counts[0], full_detail_triangles=base['models'][name]['new_triangles'],
                component=component.relative_to(K.ROOT).as_posix(), component_sha256=S.sha(component),
                staged=staged.relative_to(K.ROOT).as_posix(), staged_sha256=S.sha(staged))
            print(f'Level {level}, {name}: {counts[0]} triangles/sack', flush=True)
    assert all(S.sha(K.ROOT/p) == h for p, h in base['protected'].items())
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    totals = {level:sum(v['triangles'] for v in models.values()) for level, models in manifest['levels'].items()}
    print(json.dumps(dict(sack_triangles=totals, close_sack_triangles=sum(v['new_triangles'] for v in base['models'].values())), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=K.ROOT/'output/lowtide/quality-pass/sack-lods')
    parser.add_argument('--baseline', type=Path, default=BASE)
    parser.add_argument('--reuse-components', type=Path, help='Reviewed LOD manifest with identical close components and layout')
    args = parser.parse_args()
    generate(args.output, args.baseline, args.reuse_components)
