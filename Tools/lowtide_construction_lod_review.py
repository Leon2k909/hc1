"""Exported-geometry and pixel-size review of offline construction detail levels."""
import json
import math

import numpy as np

import map_kit as K
import lowtide_map as L
import lowtide_window_construction as W
import lowtide_door_construction as D
import lowtide_door_preview as DP
import lowtide_door_verify as DV
import lowtide_window_software as R
import lowtide_construction_lods as LD

OUT = LD.OUT/'review'


def export(model, label):
    L.configure(model)
    W.validate_model(model)
    D.validate_uvs(model)
    path = OUT/f'{label}.obj'
    K.write_obj(path, model, 'lowtide_east')
    return R.read_obj(path)


def window(level):
    wall = K.Wall('e', (-58, 58), (0, 20), (0, 196), '-n')
    opening = wall.add(0, 44, 64, 150, 'glass_arch')
    model = K.Model()
    if level:
        with LD.detail(level): W.frame(model, L, wall, opening, L.EAST)
    else: W.frame(model, L, wall, opening, L.EAST)
    return export(model, f'window-frames-{level}'), opening


def closest_count(triangles, origins, direction):
    direction = np.asarray(direction)
    a = triangles[:, 0]
    e1, e2 = triangles[:, 1]-a, triangles[:, 2]-a
    h = np.cross(direction, e2)
    det = np.sum(e1*h, axis=1)
    reciprocal = np.divide(1, det, out=np.zeros_like(det), where=abs(det) > 1e-9)
    s = origins[:, None, :]-a
    u = np.sum(s*h, axis=2)*reciprocal
    q = np.cross(s, e1)
    v = np.sum(q*direction, axis=2)*reciprocal
    t = np.sum(q*e2, axis=2)*reciprocal
    valid = (abs(det) > 1e-9) & (u > 1e-7) & (v > 1e-7) & (u+v < 1-1e-7) & (t >= 0)
    nearest = np.min(np.where(valid, t, np.inf), axis=1)
    return nearest, np.sum(valid & (abs(t-nearest[:, None]) < .002), axis=1)


def checks(frame, opening, level):
    points = frame[..., :3]
    uprights = (opening.r0+(opening.r1-opening.r0)/3, opening.r0+(opening.r1-opening.r0)*2/3)
    levels = list(np.arange(opening.z0+22, opening.spring-4, 20))+[opening.spring]
    rays = np.array([(r+side*.613, -40., z+dz) for r in uprights for side in (-1, 1)
                     for z in levels for dz in (-.113, .271)])
    nearest, counts = closest_count(points, rays, (0, 1, 0))
    assert np.isfinite(nearest).all() and np.all(counts == 1), ('Overlapping or open bar joint', level, counts)
    clear = np.array([(r, -40., 96.) for r in (-14.6, 0., 14.6)])
    assert not np.isfinite(DV.ray_hits(points, clear, (0, 1, 0))).any()
    border = np.array([(r, -40., z) for r, z in W.contour(opening, 1.3, 61)])
    assert np.isfinite(DV.ray_hits(points, border, (0, 1, 0))).all()
    coverage = 0
    for width, height in ((64., 132.), (120., 170.)):
        if level:
            with LD.detail(level): model = D.local(width, height, L.EAST.door, D.mapping())
        else: model = D.local(width, height, L.EAST.door, D.mapping())
        triangles, paints = export(model, f'door-coverage-{level}-{int(width)}')
        xx, zz = np.meshgrid(np.linspace(.003, width-.003, 37), np.linspace(.003, height-.003, 31))
        origins = np.column_stack((xx.ravel(), np.full(xx.size, 3.), zz.ravel()))
        assert np.isfinite(DV.ray_hits(triangles[..., :3], origins, (0, -1, 0), 5.01)).all()
        coverage += len(origins)
    return dict(level=level, fitted_bar_joint_rays=len(rays), clear_pane_rays=len(clear),
                frame_border_rays=len(border), closed_door_rays=coverage)


def view(kind, pixels):
    if kind == 'window':
        return dict(eye=(2.6, -5., 3.), target=(0., .1, 2.7178),
                    scale=2.1844*480/pixels, size=(640, 480))
    return dict(eye=(3.8, -8., 3.4), target=(0., 0., 2.15),
                scale=4.318*480/pixels, size=(640, 480))


def roi(kind, spec):
    eye, target = np.asarray(spec['eye'])/.0254, np.asarray(spec['target'])/.0254
    forward = K.normalise(target-eye)
    right = K.normalise(np.cross(forward, (0, 0, 1)))
    up = np.cross(right, forward)
    width, height = spec['size']
    scale = height/(spec['scale']/.0254)
    x, z0, z1 = (25., 60., 154.) if kind == 'window' else (62., 0., 170.)
    points = np.array([(a, 8., z) for a in (-x, x) for z in (z0, z1)])-eye
    xy = np.column_stack((width/2+points@right*scale, height/2-points@up*scale))
    lo = np.maximum(np.floor(xy.min(axis=0)).astype(int)-2, 0)
    hi = np.minimum(np.ceil(xy.max(axis=0)).astype(int)+2, (width, height))
    return slice(lo[1], hi[1]), slice(lo[0], hi[0])


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    wp = LD.BASE/'window-construction/preview'
    dp = LD.BASE/'door-construction/preview'
    window_high, wp_labels = R.read_obj(wp/'candidate.obj')
    door_high, dp_labels = R.read_obj(dp/'candidate.obj')
    original_out = R.OUT
    try:
        R.OUT = wp
        wm = R.materials()
    finally: R.OUT = original_out
    dm = DP.materials(json.loads((dp/'materials.json').read_text()))
    geometries = {'window': [(window_high, wp_labels)], 'door': [(door_high, dp_labels)]}
    numeric = []
    for level in (0, 1, 2):
        (frames, frame_paints), opening = window(level)
        numeric.append(checks(frames, opening, level))
        if level == 0: continue
        keep = np.array([paint != L.EAST.frame for paint in wp_labels])
        geometries['window'].append((np.concatenate((window_high[keep], frames)),
                                    [p for p, yes in zip(wp_labels, keep) if yes]+frame_paints))
        wall = K.Wall('e', (-82, 82), (0, 20), (0, 198), '-n')
        opening = wall.add(0, 120, 0, 170, 'shut')
        model = K.Model()
        with LD.detail(level): D.leaf_geometry(model, L, wall, opening, L.EAST, D.mapping())
        doors, door_paints = export(model, f'door-detail-{level}')
        keep = np.array([paint not in (L.EAST.door, D.IRON) for paint in dp_labels])
        geometries['door'].append((np.concatenate((door_high[keep], doors)),
                                  [p for p, yes in zip(dp_labels, keep) if yes]+door_paints))
    comparisons = []
    for kind, items in geometries.items():
        mats = wm if kind == 'window' else dm
        shadows = [R.shadow_map(tri) for tri, paints in items]
        for pixels in (300, 160, 80):
            spec = view(kind, pixels)
            reference = None
            for level, (triangles, paints) in enumerate(items):
                rendered = R.render(triangles, paints, mats, shadows[level], spec)
                rendered.save(OUT/f'{kind}-{pixels}px-detail{level}.png')
                values = np.asarray(rendered, float)
                if level == 0: reference = values
                else:
                    error = abs(values-reference)[roi(kind, spec)]
                    comparisons.append(dict(kind=kind, approximate_height_pixels=pixels, level=level,
                                            mean_absolute_8bit_error=float(error.mean()),
                                            changed_pixel_fraction_over_8=float(np.mean(error.max(axis=2) > 8))))
            print(f'Rendered {kind}: {pixels}px comparison', flush=True)
    report = dict(status='offline_detail_level_review', native_engine_capture=False,
                  source_manifest_sha256=W.sha(LD.OUT/'manifest.json'), source_sha256=W.sha(LD.__file__),
                  reviewer_sha256=W.sha(__file__), geometry_checks=numeric, comparisons=comparisons,
                  native_lod_thresholds=None,
                  limitations=['CPU lighting and textures; no engine normal maps, mip selection, GI or gameplay cost',
                               'Pixel differences describe these views only; they are not an acceptance metric by themselves'])
    (OUT/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(geometry_checks=numeric, comparisons=comparisons), indent=2))


if __name__ == '__main__':
    main()
