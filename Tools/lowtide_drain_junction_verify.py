"""Export/reproduction, rain-path and saved-architecture clearance checks."""
import argparse
import json
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_map as L
import lowtide_finish as F
import lowtide_drain_construction as D
import lowtide_drain_review as REVIEW
import lowtide_drain_junctions as J
import lowtide_window_construction as W
import lowtide_window_software as R


def export(model, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    L.configure(model)
    K.write_obj(path, model, F.MODEL)
    return R.read_obj(path)[0]


def geometry_checks(stage, manifest):
    baseline = json.loads((J.BASE/'manifest.json').read_text())
    old, new, details = J.build(baseline['layout'], manifest['gutters'])
    target = stage/'reproduction/junctions-new.obj'
    export(new, target)
    assert D.sha(target) == manifest['components']['junctions-new.obj']
    assert details == manifest['drains']
    original = (J.BASE/'stage/models/maps/lowtide/lowtide_finish.obj').read_text()
    old_text, new_text = [(stage/f'junctions-{v}.obj').read_text() for v in ('old', 'new')]
    expected, _ = W.replace_faces(original, old_text, new_text)
    expected = expected.replace('# cast-frame-v2', f'# {J.REVISION}')
    assert expected == (stage/'stage/models/maps/lowtide/lowtide_finish.obj').read_text()
    # The inherited gutters retain their original open support bands. Check the
    # rebuilt pipe/scupper shells and apron independently, without mislabelling
    # the older entire finish mesh as a closed solid.
    paired, path_segments = 0, 0
    for bottom in (-94., 3.):
        model = K.Model()
        record = dict(e=0., n=0., bottom=bottom, top=942., out=[0, 1, 0])
        J.warehouse(model, record)
        tri = export(model, stage/f'verification/warehouse-{bottom:g}.obj')
        paired += REVIEW.closed_mesh(tri)
        points, _ = J.warehouse_path(bottom)
        points[:, 2] += bottom
        for a, b in zip(points, points[1:]):
            length = np.linalg.norm(b-a)
            hits = REVIEW.intersections(tri, a, (b-a)/length)
            assert not len(hits) or hits.min() >= length-.002, 'Internal pipe blockage'
            path_segments += 1
    for index, gutter in enumerate(manifest['gutters']):
        model = K.Model()
        J.apron(model, gutter)
        tri = export(model, stage/f'verification/apron-{index}.obj')
        paired += REVIEW.closed_mesh(tri)
    return dict(paired_edges_in_checked_shells=paired, clear_pipe_path_segments=path_segments,
                byte_identical_reproduced_components=1, unchanged_triangles=manifest['unchanged_triangles'])


def shed_flow(stage, manifest):
    rays, drops = 0, []
    for index, gutter in enumerate(manifest['gutters']):
        model = K.Model()
        J.gutter(model, gutter)
        records = [v['updated'] for v in manifest['drains'] if v['kind'] == 'shed' and
                   v['updated']['e'] in gutter['outlets'] and
                   abs(v['updated']['n']-(gutter['n']-gutter['direction']*2.8)) < .01]
        assert len(records) == 2
        for record in records: D.drainpipe(model, L, **record)
        tri = export(model, stage/f'verification/shed-{index}.obj')
        wall = gutter['n']-gutter['direction']*2.8
        for e in gutter['outlets']:
            for x in np.linspace(e-1.35, e+1.35, 5):
                for distance in np.linspace(6.50, 7.60, 5):
                    start = (x, wall+gutter['direction']*distance, gutter['height']-1.)
                    hits = REVIEW.intersections(tri, start, np.array((0., 0., -1.)))
                    # Some samples run through the open neck and first meet
                    # the curved shoe. That is a valid continuous rain path.
                    assert len(hits) and 1.85 < hits.min() < gutter['height']+1., ('Blocked outlet or missed receiver', index, start, hits)
                    drops.append(float(hits.min()))
                    rays += 1
        # Rain leaving the folded apron falls inside the gutter, at positions
        # away from the outlets. It cannot pass behind the gutter or hit stone.
        for e in np.linspace(gutter['e0']+30., gutter['e1']-30., 11):
            start = (e, wall+gutter['direction']*5.25, gutter['height']+5.15)
            hits = REVIEW.intersections(tri, start, np.array((0., 0., -1.)))
            assert len(hits) and 5. < hits.min() < 8.5
            rays += 1
    return dict(shed_flow_rays=rays, first_receiver_hit_range=[min(drops), max(drops)],
                rays_continuing_through_pipe=sum(value > 20. for value in drops),
                outlets=16, pierced_gutters=len(manifest['gutters']))


def architecture_clearance(stage, manifest):
    # Compare rear-most drain surfaces with front-most saved masonry surfaces
    # on a grid. The new scuppers deliberately enter the wall and are excluded.
    # This exercises the actual saved OBJ, including corner returns/pilasters.
    architectures = {}
    sources = {}
    for name in ('lowtide_east', 'lowtide_west'):
        path = K.ASSETS/f'models/maps/lowtide/{name}.obj'
        tri, _ = R.read_obj(path)
        architectures[name] = (tri, tri[..., :3].min(axis=1), tri[..., :3].max(axis=1))
        sources[path.relative_to(K.ROOT).as_posix()] = D.sha(path)
    count, clearances, records = 0, [], []
    for index, detail in enumerate(manifest['drains']):
        if detail['kind'] != 'warehouse': continue
        record = detail['original']
        side = 'lowtide_east' if record['e'] > 0 else 'lowtide_west'
        tri, lo, hi = architectures[side]
        origin = np.array((record['e'], record['n'], 0.))
        outward = np.asarray(record['out'])
        basis = np.column_stack((np.cross(outward, (0, 0, 1)), outward, (0, 0, 1)))
        box = np.array([origin+basis@np.array((x, y, z)) for x in (-6., 6.) for y in (-1., 25.) for z in (899., 951.)])
        mask = np.all(hi >= box.min(axis=0), axis=1) & np.all(lo <= box.max(axis=0), axis=1)
        local = tri[mask].copy()
        local[..., :3] = (local[..., :3]-origin)@basis
        body = K.Model()
        points, tangents = J.warehouse_path(0.)
        J.swept_pipe(body, points, tangents)
        head = K.Model()
        D.hopper(head, J.WAREHOUSE_TOP)
        J.append_local(body, head, dict(e=0, n=0, bottom=0, out=[0, 1, 0]), (0, 7., 0))
        drainage = export(body, stage/f'verification/envelope-{index}.obj')
        local_values = []
        for x in np.linspace(-4.8, 4.8, 25):
            for z in np.arange(900.25, 946., .5):
                start = np.array((x, 25., z))
                direction = np.array((0., -1., 0.))
                pipe_hit = REVIEW.intersections(drainage, start, direction)
                if not len(pipe_hit): continue
                wall_hit = REVIEW.intersections(local, start, direction)
                if not len(wall_hit): continue
                clearance = float(wall_hit.min()-pipe_hit.max())
                assert clearance > .15, (index, start, clearance)
                local_values.append(clearance)
                count += 1
        assert len(local_values) > 200
        clearances.extend(local_values)
        records.append(dict(index=index, sampled_clearance=min(local_values), samples=len(local_values)))
        print(f'Checked warehouse pipe {len(records)}/20', flush=True)
    assert len(records) == 20
    return dict(saved_architecture_sources=sources, clearance_rays=count,
                minimum_sampled_clearance_inches=min(clearances), warehouse_records=records,
                clearance_scope='Upper pipe/hopper surfaces at 0.5-inch height and 0.4-inch lateral sampling; brackets/scuppers intentionally meet masonry. Not an exhaustive collision proof.')


def main(stage):
    assert not stage.resolve().is_relative_to(K.ASSETS.resolve())
    manifest = json.loads((stage/'manifest.json').read_text())
    assert D.sha(J.BASE/'manifest.json') == manifest['baseline_manifest_sha256']
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['sources'].items())
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['protected'].items())
    assert all(D.sha(stage/p) == h for p, h in manifest['components'].items())
    assert all(D.sha(stage/'stage'/p) == h for p, h in manifest['staged_files'].items())
    result = dict(status='offline_junction_checks_passed', manifest_sha256=D.sha(stage/'manifest.json'),
                  verifier_sha256=D.sha(__file__), protected_live_files=len(manifest['protected']),
                  **geometry_checks(stage, manifest), **shed_flow(stage, manifest),
                  **architecture_clearance(stage, manifest))
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['protected'].items())
    (stage/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ('warehouse_records', 'saved_architecture_sources')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    main(parser.parse_args().stage)
