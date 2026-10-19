"""Offline detail levels for the staged window and shed-door construction.

The accepted close-detail builders and live assets are untouched. Reduced
profiles are selected only inside a scoped in-memory build. No native LOD
switching is configured: the large aggregate models need runtime calibration.
"""
from contextlib import contextmanager
import gc
import json
import math
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_map as L
import lowtide_window_construction as W
import lowtide_door_construction as D
import lowtide_container_detail as C

BASE = K.ROOT/'output/lowtide/quality-pass'
OUT = BASE/'construction-lods'
REVISION = 'construction-detail-levels-v1'


def surround(model, module, wall, opening, paint, *, head_only, level):
    steps = (8 if level == 1 else 6) if head_only else (12 if level == 1 else 8)
    if head_only or level == 2:
        profile = ((0., -6.12), (0., -4.4), (2.6, -4.4), (2.6, -6.12))
    else:
        profile = ((0., -6.12), (0., -4.55), (.24, -4.25), (1.55, -4.25), (2.6, -6.12))
    contours = [W.contour(opening, inset, steps) for inset, depth in profile]
    indices = range(2, len(contours[0])-1) if head_only else range(len(contours[0]))
    outward = module.wall_out(wall)[2]
    for section, (ia, da) in enumerate(profile):
        if section == 0 or (head_only and section == len(profile)-1): continue
        following = (section+1) % len(profile)
        ib, db = profile[following]
        a, b = contours[section], contours[following]
        for j in indices:
            k = (j+1) % len(a)
            points = [W.local_point(wall, *a[j], da), W.local_point(wall, *a[k], da),
                      W.local_point(wall, *b[k], db), W.local_point(wall, *b[j], db)]
            r, z = np.subtract(a[k], a[j])
            inward = K.normalise(wall.point(-z, 0, r)-wall.point(0, 0, 0))
            towards = outward*(ib-ia)-inward*(db-da)
            normals = None
            if opening.arched and 2 <= j < len(a)-1:
                normals = []
                for index in (j, k, k, j):
                    theta = math.pi*(index-2)/steps
                    radial = wall.point(-math.cos(theta), 0, -math.sin(theta))-wall.point(0, 0, 0)
                    normals.append(K.normalise(outward*(ib-ia)-radial*(db-da)))
            D.face(model, paint, points, towards, normals=normals)


def pull(model, x, z, level):
    if level == 1:
        C.bevel_box(model, (x-.72, .015, z-4.25), (x+.72, .28, z+4.25), D.IRON, .09)
    else:
        model.box((x-.72, .015, z-4.25), (x+.72, .28, z+4.25), D.IRON)
    profile = C.rounded_profile(((.25, -2.8), (1.75, -2.3), (1.75, 2.3), (.25, 2.8)), .30, 2 if level == 1 else 1)
    sides = 6 if level == 1 else 4
    rings, normals = [], []
    for (depth, height), tangent in profile:
        cross = np.array((0., -tangent[1], tangent[0]))
        ns = [np.array((math.cos(t), 0, 0))+cross*math.sin(t)
              for t in np.linspace(0, 2*math.pi, sides, endpoint=False)]
        rings.append([np.array((x, depth, z+height))+n*.27 for n in ns])
        normals.append(ns)
    for k in range(len(rings)-1):
        for i in range(sides):
            j = (i+1) % sides
            ns = [normals[k][i], normals[k][j], normals[k+1][j], normals[k+1][i]]
            D.face(model, D.IRON, [rings[k][i], rings[k][j], rings[k+1][j], rings[k+1][i]],
                   np.mean(ns, axis=0), normals=ns)


@contextmanager
def detail(level):
    """Restore every builder after use, including on a failed verification."""
    assert level in (1, 2)
    original = dict(surround=W.surround, profile=W.BAR_PROFILE,
                    fastener=D.fastener, turned=D.turned, board=D.board, pull=D.pull)
    def reduced_board(model, *args, **kwargs):
        source = K.Model()
        original['board'](source, *args, **kwargs)
        for paint, polygons in source.polygons.items():
            for index, (points, normal) in enumerate(polygons):
                # Backing remains closed. Preserve the photographed front and
                # its edge bevels; only unresolved side/end faces are omitted.
                keep = normal[1] > .001
                if level == 1: keep |= abs(normal[1]) < .001 and abs(normal[2]) < .001
                else: keep &= abs(normal[2]) < .001
                if keep:
                    model.polygon(paint, points, normal, uv=source.polygon_uvs[(paint, index)])
    def reduced_turned(model, centre, axis, profile, sides=8):
        radius = max(p[0] for p in profile)
        a, b = profile[0][1], profile[-1][1]
        if radius <= .4 and b-a <= .35: return  # Subpixel screw heads.
        if len(profile) > 4:
            profile = (profile[0], (radius, a+.15), (radius, b-.15), profile[-1])
        original['turned'](model, centre, axis, profile, sides=min(sides, 6 if level == 1 else 4))
    try:
        W.surround = lambda m, module, wall, o, paint, head_only=False: surround(
            m, module, wall, o, paint, head_only=head_only, level=level)
        # Keep the .48-inch front shoulder at both levels: horizontal bars butt
        # against it. A wider flat front would create coplanar overlaps there.
        W.BAR_PROFILE = ((-.75, -5.97), (-.48, -4.62), (.48, -4.62), (.75, -5.97))
        D.fastener = lambda *a, **k: None
        D.turned = reduced_turned
        D.board = reduced_board
        D.pull = lambda m, x, z: pull(m, x, z, level)
        yield
    finally:
        W.surround, W.BAR_PROFILE = original['surround'], original['profile']
        D.fastener, D.turned, D.board, D.pull = (original[k] for k in ('fastener', 'turned', 'board', 'pull'))


def components(window_rows, door_rows, level):
    with detail(level):
        _, windows = W.geometry(window_rows, L)
        _, doors = D.geometry(door_rows, L, D.mapping()) if door_rows else (None, K.Model())
    model = K.Model().extend(windows).extend(doors)
    L.configure(model)
    W.validate_model(model)
    D.validate_uvs(model)
    return model


def stage():
    OUT.mkdir(parents=True, exist_ok=True)
    combined_path = BASE/'construction-integration/manifest.json'
    combined = json.loads(combined_path.read_text())
    door_path = BASE/'door-construction/manifest.json'
    doors = json.loads(door_path.read_text())
    windows = json.loads((BASE/'window-construction/layout.json').read_text())['models']
    assert all(W.sha(K.ROOT/p) == h for p, h in combined['source_manifests'].items())
    assert all(W.sha(K.ROOT/p) == h for p, h in combined['protected'].items())
    report = dict(revision=REVISION, status='offline_detail_meshes_under_review', production_changed=False,
                  native_lod_switching_configured=False, native_thresholds=None,
                  source_combined_manifest_sha256=W.sha(combined_path), levels={},
                  protected=combined['protected'],
                  sources={str(Path(p).relative_to(K.ROOT).as_posix()): W.sha(p)
                           for p in (__file__, W.__file__, D.__file__, C.__file__)})
    for level in (1, 2):
        east = components(windows['lowtide_east'], doors['selected_layout']['lowtide_east'], level)
        pairs = {'lowtide_east': east, 'lowtide_west': east.mirrored(L.WEST_PAINTS),
                 'lowtide_backdrop': components(windows['lowtide_backdrop'], [], level)}
        results = {}
        for name, model in pairs.items():
            L.configure(model)
            W.validate_model(model)
            component = OUT/f'{name}-detail{level}.obj'
            K.write_obj(component, model, name)
            # Concatenate high-detail components with adjusted OBJ indices via
            # the same exact replacement writer used for the accepted stages.
            high_window = (BASE/'window-construction'/f'{name}-new.obj').read_text()
            if name in doors['models']:
                high_door = (BASE/'door-construction'/f'{name}-new.obj').read_text()
                high, _ = W.replace_faces(high_window, '', high_door)
            else: high = high_window
            relative = f'models/maps/lowtide/{name}.obj'
            source = BASE/'construction-integration/stage'/relative
            assert W.sha(source) == combined['changes'][relative]['after']
            original = source.read_text()
            reduced = component.read_text()
            updated, removed = W.replace_faces(original, high, reduced)
            prefix, suffix = updated.rsplit(f'# {W.REVISION}\n', 1)
            updated = prefix+f'# {REVISION} level {level}\n'+suffix
            expected = W.face_keys(original, attributes=True)-W.face_keys(high, attributes=True)+W.face_keys(reduced, attributes=True)
            actual = W.face_keys(updated, attributes=True)
            assert actual == expected, 'Unrelated geometry/UV/normal change'
            target = OUT/'meshes'/f'{name}_detail{level}.obj'
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(updated.encode())
            results[name] = dict(triangles=sum(actual.values()), high_detail_triangles=combined['models'][name]['triangles'],
                                 replaced_detail_triangles=removed, reduced_detail_triangles=model.triangle_count(),
                                 output=str(target.relative_to(K.ROOT).as_posix()), sha256=W.sha(target),
                                 component_sha256=W.sha(component))
            print(f'Level {level} {name}: {sum(actual.values()):,} triangles (close level {combined["models"][name]["triangles"]:,})', flush=True)
            del expected, actual, original, updated, high
            gc.collect()
        report['levels'][str(level)] = results
    assert all(W.sha(K.ROOT/p) == h for p, h in combined['protected'].items())
    (OUT/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print('Staged geometry alternatives only; native switch calibration is pending', flush=True)


if __name__ == '__main__':
    stage()
