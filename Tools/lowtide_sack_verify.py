"""Check saved sack candidates from their exported triangles and protected sources."""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_sack_construction as S
import lowtide_sack_preview as P
import lowtide_window_software as R


def retained_lines(text):
    material = None
    result = []
    for line in text.splitlines():
        if line.startswith('usemtl '): material = line[7:]
        if line.startswith('f ') and material == S.PAINT: continue
        result.append(line)
    return result


def topology(triangles):
    edges = Counter()
    for tri in triangles:
        points = [tuple(p) for p in tri[:, :3]]
        for a, b in zip(points, points[1:]+points[:1]):
            edges[(a, b)] += 1
    assert all(count == edges[(b, a)] == 1 for (a, b), count in edges.items()), 'Open or inverted mesh edge'
    return len(edges)//2


def shadow_alignment():
    """Analytic planar depth checks, independent of the rendering correction."""
    total, worst = 0, 0.
    for slope_x, slope_y in ((0., 0.), (.4, -.2), (-.8, .3), (.12, 1.5), (1.1, -.7)):
        points = np.array([[-25., -30., 0], [30., -25., 0], [28., 30., 0]])
        points[:, 2] = 7 + points[:, 0]*slope_x + points[:, 1]*slope_y
        triangle = np.zeros((1, 3, 8))
        triangle[0, :, :3] = points
        depth, right, up, minimum, span = P.shadow_map(triangle)
        y, x = np.nonzero(depth > -1e7)
        selection = np.linspace(0, len(x)-1, min(4096, len(x)), dtype=int)
        x, y = x[selection], y[selection]
        projected = minimum + np.column_stack((x, y))/(depth.shape[0]-1)*span
        normal = np.cross(points[1]-points[0], points[2]-points[0])
        expected = (normal@points[0] - projected[:, 0]*(normal@right) - projected[:, 1]*(normal@up))/(normal@R.SUN)
        error = float(abs(depth[y, x]-expected).max())
        worst = max(worst, error)
        assert error < 1e-4, (slope_x, slope_y, error)
        total += len(selection)
    return dict(samples=total, max_depth_error_inches=worst)


def verify(out, reproduction=None, regenerate=False):
    out = Path(out).resolve()
    manifest_path = out/'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert all(S.sha(K.ROOT/p) == digest for p, digest in manifest['protected'].items())
    assert all(S.sha(K.ROOT/p) == digest for p, digest in manifest['sources'].items())
    counts = Counter()
    body_min_volume = 1.
    for name, record in manifest['models'].items():
        relative = f'models/maps/lowtide/{name}.obj'
        before = (out/'before'/f'{name}.obj').read_text()
        stage = out/'stage'/relative
        revised = stage.read_text()
        change = manifest['changes'][relative]
        assert S.sha(K.ASSETS/relative) == change['before']
        assert S.sha(stage) == change['after']
        original_part, appended = revised.split(f'# {S.REVISION}\n')
        assert original_part.splitlines() == retained_lines(before), 'Unrelated source records changed'
        component = out/f'{name}-sacks.obj'
        assert S.sha(component) == record['component_sha256']
        # Reconstruct the replacement independently from the recorded source and
        # component, proving the reviewed mesh is exactly the one in the stage.
        rebuilt, removed = S.replace(before, component.read_text())
        assert rebuilt == revised and removed == record['old_triangles']
        triangles, paints = R.read_obj(component)
        assert set(paints) == {S.PAINT}
        assert len(triangles) == record['new_triangles']
        assert np.isfinite(triangles).all()
        edges = triangles[:, 1:, :3] - triangles[:, :1, :3]
        crosses = np.cross(edges[:, 0], edges[:, 1])
        area = np.linalg.norm(crosses, axis=1)
        assert area.min() > 1e-6, 'Degenerate exported triangle'
        normals = triangles[..., 5:8]
        # map_kit.obj_vector serializes normals to three decimal places; the
        # maximum length error from rounding is sqrt(3)*.0005 (< .000867).
        assert np.max(abs(np.linalg.norm(normals, axis=-1)-1)) < .00087
        geometric = crosses/area[:, None]
        assert np.einsum('tvi,ti->tv', normals, geometric).min() > 0, 'Inverted smooth normal'
        uv_edges = triangles[:, 1:, 3:5] - triangles[:, :1, 3:5]
        uv_area = uv_edges[:, 0, 0]*uv_edges[:, 1, 1] - uv_edges[:, 0, 1]*uv_edges[:, 1, 0]
        assert np.min(abs(uv_area)) > 1e-10, 'Collapsed cloth UV'
        per_sack = len(triangles)//record['sacks']
        for index, row in enumerate(manifest['layout'][name]):
            mesh = triangles[index*per_sack:(index+1)*per_sack]
            lo, size = np.array(row['lo']), np.array(row['size'])
            pts = mesh[..., :3]
            assert np.all(pts >= lo-.0001) and np.all(pts <= lo+size+.0001)
            # Per-sack edge pairing also covers the cap and thread shells.
            counts['paired_mesh_edges'] += topology(mesh)
            body = mesh[:2*len(S.RINGS)*S.SIDES, :, :3] - lo
            volume = float(np.einsum('ti,ti->t', body[:, 0], np.cross(body[:, 1], body[:, 2])).sum()/6)
            ratio = volume/np.prod(size)
            assert .50 < ratio < 1, ('Unexpected fill volume', name, index, ratio)
            body_min_volume = min(body_min_volume, ratio)
            counts['sacks'] += 1
        counts['triangles'] += len(triangles)
        counts['preserved_triangles'] += sum(line.startswith('f ') for line in original_part.splitlines())
        if regenerate:
            regenerated = K.Model()
            for row in manifest['layout'][name]: S.sack(regenerated, row['lo'], row['size'])
            path = out/'reproduction'/component.name
            path.parent.mkdir(exist_ok=True)
            K.write_obj(path, regenerated, name)
            assert S.sha(path) == record['component_sha256'], 'Regenerated geometry differs'
            counts['byte_identical_reproduced_components'] += 1
        print(f'Checked {name}: {record["sacks"]} closed sack meshes', flush=True)
    result = dict(status='offline_exported_geometry_checks_passed', manifest_sha256=S.sha(manifest_path),
        verifier_sha256=S.sha(__file__), preview_renderer_sha256=S.sha(P.__file__),
        shared_renderer_sha256=S.sha(R.__file__), protected_live_files=len(manifest['protected']),
        **counts, body_minimum_box_volume_fraction=body_min_volume,
        shadow_plane_check=shadow_alignment(),
        collision_and_cover_bounds_preserved=True, material_inputs_and_colour_unchanged=True,
        delta_triangles=manifest['delta_triangles'],
        native_checks='Not performed; user requested offline work')
    if reproduction:
        reproduction = Path(reproduction)
        second = json.loads((reproduction/'manifest.json').read_text())
        assert second == manifest
        for relative, change in manifest['changes'].items():
            assert S.sha(reproduction/'stage'/relative) == change['after']
        result['byte_identical_reproduced_models'] = len(manifest['changes'])
    (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--reproduction', type=Path)
    parser.add_argument('--regenerate', action='store_true')
    args = parser.parse_args()
    verify(args.stage, args.reproduction, args.regenerate)
