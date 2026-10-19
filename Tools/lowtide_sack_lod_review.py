"""Exported-geometry checks and screen-size comparisons for sack detail levels.

The CPU previews choose a texture mip from each projected triangle's UV
footprint. They cannot establish native filtering, LOD transitions or FPS.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import binary_erosion, distance_transform_edt

import map_kit as K
import lowtide_sack_construction as S
import lowtide_sack_lods as D
import lowtide_sack_preview as P
import lowtide_sack_verify as V
import lowtide_window_software as R

VIEWS = {
    'oblique': dict(eye=(1.1, -1.5, .95), target=(0., 0., .12)),
    'mouth': dict(eye=(.05, -2, .40), target=(0., 0., .14)),
    'side': dict(eye=(2, -.05, .65), target=(0., 0., .14)),
}
PIXELS = (320, 160, 80)


def screen(triangles, spec):
    eye, target = np.asarray(spec['eye'])/.0254, np.asarray(spec['target'])/.0254
    forward = K.normalise(target-eye)
    right = K.normalise(np.cross(forward, (0, 0, 1)))
    up = np.cross(right, forward)
    height, width = spec['size'][1], spec['size'][0]
    factor = height/(spec['scale']/.0254)
    relative = triangles[..., :3]-eye
    projected = np.stack((width*.5 + relative@right*factor, height*.5-relative@up*factor), axis=-1)
    return projected, -relative@forward


def view_spec(triangles, view, pixels):
    spec = dict(view, size=(448, 448), scale=1.)
    xy, _ = screen(triangles, spec)
    span = np.ptp(xy.reshape(-1, 2), axis=0).max()
    spec['scale'] = span/pixels
    return spec


def silhouette(triangles, spec):
    xy, depth_values = screen(triangles, spec)
    width, height = spec['size']
    depth = np.full((height, width), -1e8, np.float32)
    image = np.zeros((height, width, 3), np.float32)
    R.PV.rasterise(image, depth, xy, depth_values, np.zeros((len(triangles), 3)))
    return depth > -1e7


def mask_error(reference, candidate):
    a, b = reference & ~binary_erosion(reference), candidate & ~binary_erosion(candidate)
    ab, ba = distance_transform_edt(~a)[b], distance_transform_edt(~b)[a]
    error = np.r_[ab, ba]
    return dict(max_edge_pixels=float(error.max()), p95_edge_pixels=float(np.quantile(error, .95)),
                changed_coverage_pixels=int(np.count_nonzero(reference ^ candidate)),
                intersection_over_union=float(np.count_nonzero(reference & candidate)/np.count_nonzero(reference | candidate)))


def mip_materials():
    source = K.ASSETS/'materials/lowtide/sacks/lt_jute_color.png'
    rgb = np.asarray(Image.open(source).convert('RGB'), np.float32)/255
    linear = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
    mips = [linear]
    while min(mips[-1].shape[:2]) > 1:
        current = mips[-1]
        h, w = current.shape[:2]
        assert h % 2 == w % 2 == 0
        mips.append(current.reshape(h//2, 2, w//2, 2, 3).mean(axis=(1, 3)))
    return {f'jute_mip_{i}':dict(texture=tex, scale=np.ones(2), rough=.95) for i, tex in enumerate(mips)}


def mip_names(triangles, spec, count):
    xy, _ = screen(triangles, spec)
    edges = xy[:, 1:] - xy[:, :1]
    tex = (triangles[:, 1:, 3:5] - triangles[:, :1, 3:5])*1024
    determinant = edges[:, 0, 0]*edges[:, 1, 1] - edges[:, 0, 1]*edges[:, 1, 0]
    valid = abs(determinant) > 1e-7
    gradients = np.zeros_like(tex)
    gradients[valid] = np.linalg.solve(edges[valid], tex[valid])
    footprint = np.linalg.norm(gradients, axis=-1).max(axis=-1)
    levels = np.clip(np.rint(np.log2(np.maximum(footprint, 1))), 0, count-1).astype(int)
    return [f'jute_mip_{i}' for i in levels]


def geometry(out, manifest, base, baseline):
    counts = Counter()
    for name in base['models']:
        high, _ = R.read_obj(baseline/f'{name}-sacks.obj')
        attributes = {tuple(vertex) for vertex in high.reshape(-1, 8)}
        before = (baseline/'before'/f'{name}.obj').read_text()
        for level, models in manifest['levels'].items():
            entry = models[name]
            component, stage = K.ROOT/entry['component'], K.ROOT/entry['staged']
            assert S.sha(component) == entry['component_sha256'] and S.sha(stage) == entry['staged_sha256']
            updated, removed = S.replace(before, component.read_text())
            assert updated == stage.read_text() and removed == base['models'][name]['old_triangles']
            libraries = [line.split(maxsplit=1)[1] for line in updated.splitlines() if line.startswith('mtllib ')]
            assert len(libraries) == 1
            library = stage.parent/libraries[0]
            entry_library = manifest['material_libraries'][library.relative_to(K.ROOT).as_posix()]
            assert S.sha(library) == S.sha(K.ROOT/entry_library['source']) == entry_library['sha256']
            materials = {line.split(maxsplit=1)[1] for line in library.read_text().splitlines() if line.startswith('newmtl ')}
            used = {line.split(maxsplit=1)[1] for line in updated.splitlines() if line.startswith('usemtl ')}
            assert used <= materials, 'Staged OBJ refers to missing material slots'
            counts['current_material_libraries'] += 1
            counts['preserved_triangles'] += sum(line.startswith('f ') for line in V.retained_lines(before))
            triangles, paints = R.read_obj(component)
            assert set(paints) == {S.PAINT} and len(triangles) == entry['triangles']
            assert np.isfinite(triangles).all()
            assert all(tuple(vertex) in attributes for vertex in triangles.reshape(-1, 8)), 'A retained body attribute moved'
            edges = triangles[:, 1:, :3]-triangles[:, :1, :3]
            cross = np.cross(edges[:, 0], edges[:, 1])
            area = np.linalg.norm(cross, axis=1)
            assert area.min() > 1e-6
            assert np.einsum('tvi,ti->tv', triangles[..., 5:8], cross/area[:, None]).min() > 0
            uv = triangles[:, 1:, 3:5]-triangles[:, :1, 3:5]
            assert abs(uv[:, 0, 0]*uv[:, 1, 1]-uv[:, 0, 1]*uv[:, 1, 0]).min() > 1e-10
            count = entry['per_sack_triangles']
            for index, row in enumerate(base['layout'][name]):
                mesh = triangles[index*count:(index+1)*count]
                lo, size = np.array(row['lo']), np.array(row['size'])
                assert (mesh[..., :3] >= lo-.0001).all() and (mesh[..., :3] <= lo+size+.0001).all()
                counts['paired_edges'] += V.topology(mesh)
                counts['closed_sacks'] += 1
            counts['retained_vertex_attributes'] += len(triangles)*3
            print(f'Checked level {level}, {name}', flush=True)
    return dict(counts)


def previews(out, base):
    directory = out/'preview'
    directory.mkdir(exist_ok=True)
    # Two physical seeds, evaluated from three directions at each screen size.
    seeds = [S.seed_for(base['layout']['lowtide_dress_east'][0]['lo']),
             S.seed_for(base['layout']['lowtide_fleet'][-1]['lo'])]
    mats = mip_materials()
    metrics, exported = [], {}
    for sample, seed in enumerate(seeds):
        triangles, shadows = {}, {}
        for level in (0, 1, 2):
            model = K.Model()
            D.sack(model, (-10.5, -16.5, 0), (21, 33, 11), level, seed=seed)
            path = directory/f'sample-{sample}-level-{level}.obj'
            K.write_obj(path, model, 'sack-lod-review')
            exported[path.name] = S.sha(path)
            triangles[level], _ = R.read_obj(path)
            shadows[level] = P.shadow_map(triangles[level])
        for name, view in VIEWS.items():
            for size in PIXELS:
                spec = view_spec(triangles[0], view, size)
                masks = {level:silhouette(triangles[level], spec) for level in (0, 1, 2)}
                for level in (1, 2):
                    metrics.append(dict(sample=sample, view=name, size=size, level=level,
                                        **mask_error(masks[0], masks[level])))
                if sample: continue
                sheet = Image.new('RGB', (448*3, 480), (26, 28, 29))
                for level in (0, 1, 2):
                    names = mip_names(triangles[level], spec, len(mats))
                    rendered = R.render(triangles[level], names, mats, shadows[level], spec)
                    sheet.paste(rendered, (448*level, 24))
                    text = f'{"CLOSE" if level == 0 else "LEVEL "+str(level)} | {len(triangles[level])} triangles | {size}px feature'
                    ImageDraw.Draw(sheet).text((448*level+12, 8), text, fill=(230, 230, 225))
                ImageDraw.Draw(sheet).text((12, 465), 'OFFLINE CPU COMPARISON | approximate mip filtering | native transitions and performance unverified', fill=(220, 220, 215))
                sheet.save(directory/f'{name}-{size}.png')
        print(f'Compared seed {sample} at 320/160/80 pixels', flush=True)
    provenance = dict(native_engine_capture=False, geometry_sources_sha256={
        p.relative_to(K.ROOT).as_posix():S.sha(p) for p in (Path(D.__file__), Path(S.__file__))},
        renderer_sources_sha256={p.relative_to(K.ROOT).as_posix():S.sha(p) for p in (Path(__file__), Path(P.__file__), Path(R.__file__))},
        exported_meshes=exported, previews={p.name:S.sha(p) for p in sorted(directory.glob('*.png'))},
        views=VIEWS, feature_pixels=list(PIXELS),
        limitations=['Nearest mip chosen per orthographic triangle; not native anisotropic/trilinear filtering',
                     'No engine GI, normal map shading, temporal LOD switching or performance measurement',
                     'Two representative seed variants; silhouette results are not an exhaustive visual proof'])
    (directory/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')
    return metrics


def main(out, geometry_only=False):
    out = Path(out).resolve()
    assert out.is_relative_to(K.ROOT/'output/lowtide/quality-pass')
    path = out/'manifest.json'
    manifest = json.loads(path.read_text())
    baseline_path = (K.ROOT/manifest['baseline_manifest']).resolve()
    assert baseline_path.is_relative_to(K.ROOT/'output/lowtide/quality-pass')
    assert Path(manifest['project_root']).resolve() == K.ROOT
    base = json.loads(baseline_path.read_text())
    assert manifest['baseline_manifest_sha256'] == S.sha(baseline_path)
    assert all(S.sha(K.ROOT/p) == h for p, h in manifest['sources'].items())
    assert all(S.sha(K.ROOT/p) == h for p, h in manifest['protected'].items())
    checked = geometry(out, manifest, base, baseline_path.parent)
    comparison = [] if geometry_only else previews(out, base)
    reductions = {level:sum(v['triangles'] for v in models.values()) for level, models in manifest['levels'].items()}
    result = dict(status='offline_exported_geometry_checks_passed' if geometry_only else 'offline_geometry_and_screen_comparisons_complete',
        manifest_sha256=S.sha(path), reviewer_sha256=S.sha(__file__),
        **checked, protected_live_files=len(manifest['protected']), reduced_sack_triangles=reductions,
        silhouette_comparisons=comparison, native_switching_configured=False,
        native_checks='Deferred by the user; runtime cost and temporal appearance unverified')
    assert all(S.sha(K.ROOT/p) == h for p, h in manifest['protected'].items())
    (out/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    maxima = {} if geometry_only else {f'level-{level}-{size}px': max(row['max_edge_pixels'] for row in comparison if row['level']==level and row['size']==size)
               for level in (1, 2) for size in PIXELS}
    print(json.dumps(dict(**checked, reduced_sack_triangles=reductions, max_silhouette_error_pixels=maxima), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=K.ROOT/'output/lowtide/quality-pass/sack-lods')
    parser.add_argument('--geometry-only', action='store_true', help='Verify rebased exports without repeating unchanged component previews')
    args = parser.parse_args()
    main(args.output, args.geometry_only)
