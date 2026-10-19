"""Independently check staged ground-detail OBJ geometry and placement guards."""
from collections import Counter
import json
from pathlib import Path

import numpy as np

import belltower_ground_edges as G


def read_obj(path):
    vertices, uvs, normals, triangles, materials = [], [], [], [], set()
    for line in path.read_text(encoding='utf-8').splitlines():
        tokens = line.split()
        if not tokens:
            continue
        if tokens[0] == 'v':
            # map_kit writes plan (e,n,z) as OBJ (-e,z,n).
            x, y, z = map(float, tokens[1:])
            vertices.append([-x, z, y])
        elif tokens[0] == 'vt':
            uvs.append(list(map(float, tokens[1:])))
        elif tokens[0] == 'vn':
            x, y, z = map(float, tokens[1:])
            normals.append([-x, z, y])
        elif tokens[0] == 'usemtl':
            materials.add(tokens[1])
        elif tokens[0] == 'f':
            assert len(tokens) == 4, 'Non-triangle face'
            triangle = [tuple(int(v) - 1 for v in token.split('/')) for token in tokens[1:]]
            assert all(0 <= v < len(vertices) and 0 <= uv < len(uvs) and 0 <= n < len(normals) for v, uv, n in triangle)
            triangles.append(triangle)
    assert materials == {G.PAINT}
    vertices, uvs, normals = map(np.asarray, (vertices, uvs, normals))
    assert np.isfinite(vertices).all() and np.isfinite(uvs).all() and np.isfinite(normals).all()
    assert np.all((uvs >= 0) & (uvs <= 1))
    assert np.allclose(normals, (0, 0, 1), atol=1e-5)
    for triangle in triangles:
        points = vertices[[v for v, _, _ in triangle]]
        assert np.cross(points[1] - points[0], points[2] - points[0])[2] > 1e-5, 'Flipped or degenerate face'
    return vertices, uvs, triangles


def check_placement(points, front, paving):
    assert points.shape == (4, 3) and np.allclose(points[:, 2], G.HEIGHT, atol=.0006)
    along = np.array([1., 0.]) if front['axis'] == 'e' else np.array([0., 1.])
    out = np.asarray(front['normal'])
    origin = np.array([0., front['depth']]) if front['axis'] == 'e' else np.array([front['depth'], 0.])
    run = points[:, :2] @ along
    assert run.min() >= front['run'][0] + 7 - .001 and run.max() <= front['run'][1] - 7 + .001
    for lo, hi in front['protected_openings']:
        assert run.max() <= lo + .001 or run.min() >= hi - .001, 'Door/shop opening clearance violated'
    distance = (points[:, :2] - origin) @ out
    assert distance.min() >= 2.55 - .001, 'Wall/plinth clearance violated'
    assert distance.max() < 22, 'Patch extends too far from the building'
    assert any(np.all(points[:, :2] >= lo - .001) and np.all(points[:, :2] <= hi + .001) for lo, hi in paving), 'Patch leaves existing flat paving'


def main():
    manifest_path = G.STAGE / 'manifest.json'
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    assert len(data['files']) == 9 and not data['live_assets_written']
    for source, expected in data['source_sha256'].items():
        assert G.sha(G.ROOT / source) == expected, source
    for record in data['files']:
        assert G.sha(G.ROOT / record['source']) == record['sha256'], record['source']
    assert G.sha(G.STAGE / 'Assets' / G.TEXTURE) == G.sha(G.SOURCE)
    fronts = {front['key']: front for front in data['frontages']}
    paving = G.paving_rectangles()
    vertices, uvs, faces = read_obj(G.STAGE / 'Assets' / G.RESOURCE / 'belltower_ground_edge_west.obj')
    count = data['patches_per_half']
    assert len(vertices) == count * 4 and len(faces) == count * 2 == data['triangles_per_half']
    assert count == len(data['patches']) and len(uvs) == len(vertices)
    for index, patch in enumerate(data['patches']):
        points = vertices[index * 4:index * 4 + 4]
        assert np.allclose(points, patch['points'], atol=.0006)
        check_placement(points, fronts[patch['front']], paving)
        sides = [np.linalg.norm(points[(k + 1) % 4] - points[k]) for k in range(4)]
        # OBJ positions have three decimal places in inches. A 2D edge can
        # therefore differ by sqrt(2)*.001 inches after endpoint rounding.
        export_error = np.sqrt(2) * .001 + 1e-7
        assert abs(sides[0] - patch['width']) <= export_error and abs(sides[1] - patch['depth']) <= export_error, 'Atlas was stretched'
        assert np.isclose(patch['width'] / patch['depth'], data['atlas_regions'][patch['atlas']]['aspect'], atol=1e-10)
        region = data['atlas_regions'][patch['atlas']]['uv']
        expected = {(round(u, 5), round(v, 5)) for u in (region[0], region[2]) for v in (region[1], region[3])}
        actual = {(round(u, 5), round(v, 5)) for u, v in uvs[index * 4:index * 4 + 4]}
        assert actual == expected, 'Quad samples another atlas region'
        # The thin atlas's dense upper edge must face the wall, rather than
        # putting its straight side out on the open paving.
        patch_uv = uvs[index * 4:index * 4 + 4]
        wall_distance = points[:, :2] @ np.asarray(fronts[patch['front']]['normal'])
        back = np.isclose(patch_uv[:, 1], region[3], atol=1e-5)
        assert back.sum() == 2 and wall_distance[back].mean() < wall_distance[~back].mean()
    east, east_uvs, east_faces = read_obj(G.STAGE / 'Assets' / G.RESOURCE / 'belltower_ground_edge_east.obj')
    mirrored = vertices.copy()
    mirrored[:, 0] *= -1
    points_key = lambda points: Counter(tuple(np.round(p, 3)) for p in points)
    assert points_key(east) == points_key(mirrored)
    assert len(east_faces) == len(faces) and len(east_uvs) == len(uvs)
    for side in ('west', 'east'):
        text = (G.STAGE / 'Assets' / G.RESOURCE / f'belltower_ground_edge_{side}.vmdl').read_text()
        assert 'PhysicsShape' not in text and 'PhysicsHull' not in text

    # Exercise the two spatial checks against actual bad placements rather than
    # treating a successful generator run as proof that the guards detect errors.
    fixture_index = next(i for i, patch in enumerate(data['patches']) if fronts[patch['front']]['protected_openings'])
    patch = data['patches'][fixture_index]
    front = fronts[patch['front']]
    points = vertices[fixture_index * 4:fixture_index * 4 + 4].copy()
    axis = 0 if front['axis'] == 'e' else 1
    points[:, axis] += np.mean(front['protected_openings'][0]) - points[:, axis].mean()
    try:
        check_placement(points, front, paving)
    except AssertionError as error:
        assert str(error) == 'Door/shop opening clearance violated'
    else:
        raise AssertionError('The doorway guard accepted a blocked threshold')
    points = vertices[fixture_index * 4:fixture_index * 4 + 4].copy()
    points[:, :2] -= np.asarray(front['normal']) * 4
    try:
        check_placement(points, front, paving)
    except AssertionError as error:
        assert str(error) == 'Wall/plinth clearance violated'
    else:
        raise AssertionError('The wall guard accepted an embedded patch')
    report = dict(passed=True, manifest_sha256=G.sha(manifest_path), checker_sha256=G.sha(Path(__file__)),
                  patches_per_half=count, triangles_total=len(faces) + len(east_faces), materials=1,
                  flat_paving_containment=True, protected_thresholds_clear=True, wall_plinth_clear=True,
                  exact_mirror=True, atlas_aspect_and_regions_preserved=True,
                  original_pixels_and_alpha_preserved=True, authored_physics_shapes=0,
                  negative_door_and_wall_fixtures_rejected=True, native_verified=False)
    (G.STAGE / 'geometry-checks.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    main()
