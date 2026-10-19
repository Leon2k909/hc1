"""Offline construction candidate for Lowtide's four sheds' loading doors.

Read-only layout capture and exact face replacement. Live materials, upper
doors, thresholds, collision and scene files are preserved. Nothing is imported
or connected to the canonical map writer before native review.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_container_detail as C
import lowtide_doors as D
import lowtide_window_construction as W

REVISION = 'shed-timber-and-iron-v2'
DETAIL_SILL_MAX = 320.0
IRON = 'iron_black'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def collect(L):
    original = L.leaves_shut
    result = {}
    try:
        for name, builder in (('lowtide_east', L.half), ('lowtide_backdrop', L.backdrop)):
            rows = []
            def record(model, wall, opening, style):
                if opening.z0 <= DETAIL_SILL_MAX:
                    rows.append(dict(axis=wall.axis, run=wall.run, across=wall.across,
                                     wall_z=wall.z, outward=wall.outward,
                                     opening=[opening.r0, opening.r1, opening.z0, opening.z1, opening.kind],
                                     style=vars(style)))
            L.leaves_shut = record
            builder()
            result[name] = rows
    finally:
        L.leaves_shut = original
    return result


def selected(row, L):
    wall, opening, _ = W.unpack(row, L)
    if abs(opening.z0) > .01: return False
    depth, _ = wall.outer()
    east, north, _ = wall.point((opening.r0+opening.r1)*.5, depth, opening.z0)
    for e0, e1, n0, n1 in (L.YARD_SHED, L.QUAY_SHED):
        if e0-.01 <= east <= e1+.01 and n0-.01 <= north <= n1+.01:
            if min(abs(east-e0), abs(east-e1), abs(north-n0), abs(north-n1)) < .01:
                return True
    return False


def face(model, paint, points, normal, uv=None, normals=None):
    points = np.asarray(points, float)
    if np.dot(np.cross(points[1]-points[0], points[2]-points[0]), normal) < 0:
        points = points[::-1]
        if uv is not None: uv = list(reversed(uv))
        if normals is not None: normals = list(reversed(normals))
    model.polygon(paint, points, normal, uv=uv, normals=normals)


def board(model, x0, x1, z0, z1, paint, index, mapping, *, front=0, back=-.65):
    """Bevelled timber with a complete photographed board on its front face.

    Explicit UVs account for the material's cropped atlas and OBJ V flip.
    The generated colour files are sampled directly, never rewritten.
    """
    joints, scale = mapping
    slot = index % (len(joints)-1)
    u0, u1 = joints[slot:slot+2]
    # Stop just inside the photographed groove: geometry supplies the seam.
    a, b = u0+(u1-u0)*.028, u1-(u1-u0)*.028
    phase = .992 - (index % 3)*.027
    shape = K.Model()
    C.bevel_box(shape, (x0, back, z0), (x1, front, z1), paint, .11)
    for points, normal in shape.polygons[paint]:
        projection = int(np.argmax(np.abs(normal)))
        uv = []
        for x, y, z in points:
            across = (x-x0)/(x1-x0)
            if projection == 0:
                across = (.025 if normal[0] < 0 else .975) + (front-y)*.018
            u = (a+(b-a)*across)/scale[0]
            v = 1+(z-z0)/D.TILE_UNITS-phase/scale[1]
            if projection == 2:
                v = 1+(front-y)/D.TILE_UNITS-phase/scale[1]
            uv.append((u, v))
        model.polygon(paint, points, normal, uv=uv)


def plate(model, outline, back, front, bevel=.055):
    """A convex forged plate with a small bevel instead of a square box edge."""
    outline = np.asarray(outline, float)
    centre = outline.mean(axis=0)
    inner = outline.copy()
    direction = centre-outline
    inner += direction/np.maximum(np.linalg.norm(direction, axis=1, keepdims=True), 1e-8)*bevel
    def ring(points, depth): return [np.array((r, depth, z)) for r, z in points]
    rear, outer, lip = ring(outline, back), ring(outline, front-bevel), ring(inner, front)
    face(model, IRON, lip, (0, 1, 0))
    for i in range(len(outline)):
        j = (i+1) % len(outline)
        away = np.r_[((outline[i]+outline[j])*.5-centre)[0], 0,
                     ((outline[i]+outline[j])*.5-centre)[1]]
        face(model, IRON, [rear[i], rear[j], outer[j], outer[i]], away)
        face(model, IRON, [outer[i], outer[j], lip[j], lip[i]], away+np.array((0, 2, 0)))


def turned(model, centre, axis, profile, sides=8):
    centre, axis = np.asarray(centre), K.normalise(axis)
    u = K.normalise(np.cross(axis, (1, 0, 0) if abs(axis[0]) < .9 else (0, 1, 0)))
    v = np.cross(axis, u)
    radials = [u*math.cos(t)+v*math.sin(t) for t in np.linspace(0, 2*math.pi, sides, endpoint=False)]
    for (ra, a), (rb, b) in zip(profile, profile[1:]):
        for i in range(sides):
            j = (i+1) % sides
            pts = [centre+axis*a+radials[i]*ra, centre+axis*a+radials[j]*ra,
                   centre+axis*b+radials[j]*rb, centre+axis*b+radials[i]*rb]
            normal = (radials[i]+radials[j])*.5*(b-a)-axis*(rb-ra)
            normals = [K.normalise(radials[k]*(b-a)-axis*(rb-ra)) for k in (i, j, j, i)]
            if rb == 0: pts, normals = pts[:3], normals[:3]
            elif ra == 0: pts, normals = pts[1:], normals[1:]
            face(model, IRON, pts, normal, normals=normals)
    radius, along = profile[-1]
    if radius:
        face(model, IRON, [centre+axis*along+r*radius for r in radials], axis)


def fastener(model, x, z, front=.29):
    turned(model, (x, front, z), (0, 1, 0), ((.38, 0), (.34, .10), (0, .27)))


def hinge(model, outer, direction, z, width):
    length = min(width*.78, 43.)
    # A tapered strap with a rounded end, attached to its pintle barrel.
    outline = [(0, -1.6), (length-1, -.85)]
    outline += [(length-1+.85*math.cos(t), .85*math.sin(t)) for t in np.linspace(-math.pi/2, math.pi/2, 7)[1:]]
    outline += [(0, 1.6)]
    plate(model, [(outer+direction*r, z+dz) for r, dz in outline], .025, .29)
    for along in (3.2, length*.48, length-3): fastener(model, outer+direction*along, z)
    turned(model, (outer, .50, z), (0, 0, 1),
           ((.34, -3.2), (.48, -3.05), (.48, -1.1), (.39, -1.0), (.48, -.9),
            (.48, .9), (.39, 1.), (.48, 1.1), (.48, 3.05), (.34, 3.2)), sides=10)
    # The centre knuckle is held by a pintle entering a fixed reveal bracket.
    # Its mounting face lies against the masonry rather than floating on timber.
    jamb = outer-direction*.85
    a, b = sorted((jamb-direction*.12, jamb+direction*.18))
    C.bevel_box(model, (a, -1.4, z-2.2), (b, .64, z+2.2), IRON, .06)
    turned(model, (jamb-direction*.12, .50, z), (direction, 0, 0), ((.24, 0), (.24, .97)), sides=8)
    for dz in (-1.45, 1.45):
        turned(model, (jamb+direction*.18, -.60, z+dz), (direction, 0, 0),
               ((.31, 0), (.27, .09), (0, .20)), sides=8)


def pull(model, x, z):
    C.bevel_box(model, (x-.72, .015, z-4.25), (x+.72, .28, z+4.25), IRON, .09)
    for height in (z-3.55, z+3.55): fastener(model, x, height, .28)
    # Curved standoffs leave a real opening behind a vertical forged grip.
    profile = C.rounded_profile(((.25, -2.8), (1.75, -2.3), (1.75, 2.3), (.25, 2.8)), .30, 3)
    rings, ns = [], []
    for (depth, height), tangent in profile:
        cross = np.array((0., -tangent[1], tangent[0]))
        normals = [np.array((math.cos(t), 0, 0))+cross*math.sin(t)
                   for t in np.linspace(0, 2*math.pi, 8, endpoint=False)]
        rings.append([np.array((x, depth, z+height))+normal*.27 for normal in normals])
        ns.append(normals)
    for k in range(len(rings)-1):
        for i in range(8):
            j = (i+1) % 8
            normals = [ns[k][i], ns[k][j], ns[k+1][j], ns[k+1][i]]
            face(model, IRON, [rings[k][i], rings[k][j], rings[k+1][j], rings[k+1][i]],
                 np.mean(normals, axis=0), normals=normals)


def local(width, height, paint, mapping, seed=0):
    model = K.Model()
    # Full closed backing retains opacity through every small board joint.
    backing = K.Model()
    backing.box((0, -2, 0), (width, -.64, height), paint)
    for points, normal in backing.polygons[paint]:
        model.polygon(paint, points, normal)
    half = width*.5
    for leaf, (a, b, outer, direction) in enumerate(((0., half-.055, .85, 1.),
                                                    (half+.055, width, width-.85, -1.))):
        count = max(2, round((b-a)/D.BOARD_WIDTH))
        pitch = (b-a)/count
        for index in range(count):
            board(model, a+index*pitch+.032, a+(index+1)*pitch-.032, 0, height,
                  paint, index+leaf*3+seed % 12, mapping)
        levels = [14., height-14.]
        if height > 145: levels.insert(1, height*.53)
        for z in levels: hinge(model, outer, direction, z, b-a)
        pull(model, half+(-3.2 if leaf == 0 else 3.2), min(43., height*.43))
    # A metal overlapping centre strip hides the meeting joint, as on the old
    # door, but catches light with a formed edge instead of an unbroken box.
    C.bevel_box(model, (half-.85, .015, 0), (half+.85, .35, height), IRON, .09)
    latch_z = min(43., height*.43)-7.5
    plate(model, ((half-5, latch_z-.65), (half+3.5, latch_z-.65),
                  (half+4.1, latch_z), (half+3.5, latch_z+.65), (half-5, latch_z+.65)), .38, .64)
    fastener(model, half-4.1, latch_z, .64)
    keeper = half+2.45
    C.bevel_box(model, (keeper-.8, .015, latch_z-1.7), (keeper+.8, .27, latch_z+1.7), IRON, .075)
    for dz in (-1.35, 1.35): fastener(model, keeper, latch_z+dz, .27)
    # A fixed staple has two feet on the plate and an open throat for the hasp.
    for dz in (-1.02, 1.02):
        C.bevel_box(model, (keeper-.225, .25, latch_z+dz-.20),
                    (keeper+.225, 1.10, latch_z+dz+.20), IRON, .06)
    C.bevel_box(model, (keeper-.225, .88, latch_z-1.02),
                (keeper+.225, 1.10, latch_z+1.02), IRON, .06)
    return model


def leaf_geometry(model, L, wall, opening, style, mapping):
    seed = L.keyed(wall.axis, wall.run, wall.across, opening.r0, 'door boards')
    source = local(opening.r1-opening.r0, opening.z1-opening.z0, style.door, mapping, seed)
    d, sign, outward = L.wall_out(wall)
    along = wall.point(1, 0, 0)-wall.point(0, 0, 0)
    basis = np.column_stack((along, outward, (0., 0., 1.)))
    origin = wall.point(opening.r0, d-sign*8, opening.z0)
    for paint, items in source.polygons.items():
        for index, (points, normal) in enumerate(items):
            normals = source.polygon_normals.get((paint, index))
            face(model, paint, [origin+basis@p for p in points], basis@normal,
                 uv=source.polygon_uvs.get((paint, index)),
                 normals=[basis@n for n in normals] if normals is not None else None)


def mapping():
    _, _, joints, _, _, scale = D.surface()
    fractions = (joints-joints[0])/(joints[-1]-joints[0])
    return fractions, scale


def geometry(rows, L, uv_mapping):
    old, new = K.Model(), K.Model()
    for row in rows:
        wall, opening, style = W.unpack(row, L)
        original = K.Model()
        L.leaves_shut(original, wall, opening, style)
        for paint in (style.door, IRON):
            for points, normal in original.polygons[paint]: old.polygon(paint, points, normal)
        leaf_geometry(new, L, wall, opening, style, uv_mapping)
    L.configure(old); L.configure(new)
    assert not old.boxes and not new.boxes and not old.hulls and not new.hulls
    return old, new


def validate_uvs(model):
    count = 0
    for (paint, index), coords in model.polygon_uvs.items():
        uv = np.asarray(coords)
        assert np.isfinite(uv).all()
        for i in range(1, len(uv)-1):
            a, b = uv[i]-uv[0], uv[i+1]-uv[0]
            assert abs(a[0]*b[1]-a[1]*b[0]) > 1e-11, (paint, index, 'collapsed UV')
            count += 1
    return count


def stage(out):
    import lowtide_map as L
    out = Path(out).resolve()
    assert not out.is_relative_to(K.ASSETS.resolve()), 'Stage outside live Assets'
    out.mkdir(parents=True, exist_ok=True)
    layout_path = out/'layout.json'
    if layout_path.exists():
        saved = json.loads(layout_path.read_text())
        assert saved['map_source_sha256'] == sha(L.__file__), 'Layout changed; choose a new stage'
        rows = saved['models']
    else:
        rows = collect(L)
        layout_path.write_text(json.dumps(dict(map_source_sha256=sha(L.__file__), models=rows), indent=2)+'\n')
    protected = {p.relative_to(K.ROOT).as_posix(): sha(p)
                 for folder in ('Assets/models/maps/lowtide', 'Assets/materials/lowtide', 'Assets/scenes/maps/Lowtide')
                 for p in (K.ROOT/folder).rglob('*') if p.is_file() and not p.name.endswith('_c')}
    available = {name: len(items) for name, items in rows.items()}
    rows = {name: [row for row in items if selected(row, L)] for name, items in rows.items()}
    uv_mapping = mapping()
    old, new = geometry(rows['lowtide_east'], L, uv_mapping)
    pairs = {'lowtide_east': (old, new),
             'lowtide_west': (old.mirrored(L.WEST_PAINTS), new.mirrored(L.WEST_PAINTS))}
    if rows['lowtide_backdrop']: pairs['lowtide_backdrop'] = geometry(rows['lowtide_backdrop'], L, uv_mapping)
    report = dict(revision=REVISION, status='offline_candidate_under_review', production_changed=False,
                  scope='Six closed door pairs on each side: the yard and quay sheds only',
                  available_lower_doors=available, selected_layout=rows,
                  protected=protected, changes={}, models={}, new_material_slots=0)
    for name, (before, after) in pairs.items():
        W.validate_model(after)
        uv_triangles = validate_uvs(after)
        L.configure(before); L.configure(after)
        for label, model in (('old', before), ('new', after)):
            K.write_obj(out/f'{name}-{label}.obj', model, name)
        source = L.OUT_DIR/f'{name}.obj'
        text = source.read_text()
        old_text, new_text = (out/f'{name}-old.obj').read_text(), (out/f'{name}-new.obj').read_text()
        revised, removed = W.replace_faces(text, old_text, new_text)
        prefix, suffix = revised.rsplit(f'# {W.REVISION}\n', 1)
        revised = prefix+f'# {REVISION}\n'+suffix
        expected = W.face_keys(text, attributes=True)-W.face_keys(old_text, attributes=True)+W.face_keys(new_text, attributes=True)
        # Removed old attributes may depend on the original world's UV offset;
        # exact counters certify every unrelated triangle, including windows.
        assert W.face_keys(revised, attributes=True) == expected, 'Unexpected geometry or attribute delta'
        for paint in after.polygons:
            assert f'from = "{paint}.vmat"' in source.with_suffix('.vmdl').read_text(), paint
        target = out/'stage/models/maps/lowtide'/source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(revised.encode())
        baseline = out/'before'/source.name
        baseline.parent.mkdir(exist_ok=True)
        if baseline.exists(): assert baseline.read_bytes() == source.read_bytes(), 'Live source changed since staging'
        else: baseline.write_bytes(source.read_bytes())
        report['changes'][source.relative_to(K.ASSETS).as_posix()] = dict(before=sha(source), after=sha(target))
        count = len(rows['lowtide_east' if name == 'lowtide_west' else name])
        report['models'][name] = dict(doors=count, removed_triangles=removed, added_triangles=after.triangle_count(),
                                      preserved_triangles=sum(W.face_keys(text).values())-removed,
                                      noncollapsed_explicit_uv_triangles=uv_triangles)
    assert all(sha(K.ROOT/p) == h for p, h in protected.items()), 'Live assets changed during offline staging'
    report['delta_triangles'] = sum(v['added_triangles']-v['removed_triangles'] for v in report['models'].values())
    report['generator_sources'] = {str(Path(p).relative_to(K.ROOT).as_posix()): sha(p)
                                   for p in (__file__, C.__file__, D.__file__, W.__file__)}
    (out/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ('protected', 'changes', 'selected_layout')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
