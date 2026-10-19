"""Compose drainage junction repairs over the existing offline drain candidate.

Shed hoppers sit below pierced gutters. Warehouse pipes stand clear of the
pilasters and bend around the cornice to hoppers supplied by open scuppers.
Only lowtide_finish draw triangles change; all live assets remain read-only.
"""
import argparse
import json
import math
from pathlib import Path
import shutil

import numpy as np

import map_kit as K
import lowtide_map as L
import lowtide_finish as F
import lowtide_drain_construction as D
import lowtide_window_construction as W

BASE = K.ROOT/'output/lowtide/quality-pass/drain-construction'
REVISION = 'connected-drainage-v2'
WAREHOUSE_TOP = 946.


def append_local(model, local, record, shift=(0, 0, 0)):
    out = np.asarray(record['out'], float)
    basis = np.column_stack((np.cross(out, (0, 0, 1)), out, (0, 0, 1)))
    origin = np.array((record['e'], record['n'], record['bottom']))
    shift = np.asarray(shift)
    for paint, faces in local.polygons.items():
        for index, (points, normal) in enumerate(faces):
            ns = local.polygon_normals.get((paint, index))
            model.polygon(paint, [basis@(p+shift)+origin for p in points], basis@normal,
                          uv=local.polygon_uvs.get((paint, index)),
                          normals=[basis@n for n in ns] if ns is not None else None)


def swept_pipe(model, points, tangents):
    points, tangents = np.asarray(points), np.asarray(tangents)
    angles = np.linspace(0, 2*math.pi, D.SIDES, endpoint=False)
    radial = np.array([np.cos(angles)[:, None]*np.array((1., 0., 0.))+
                       np.sin(angles)[:, None]*np.cross(t, (1., 0., 0.)) for t in tangents])
    distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
    rings = []
    for radius, sign in ((2., 1), (1.7, -1)):
        vertices = points[:, None, :]+radial*radius
        rings.append(vertices)
        for row in range(len(points)-1):
            for j in range(D.SIDES):
                k = (j+1) % D.SIDES
                ids = ((row, j), (row, k), (row+1, k), (row+1, j))
                pts = [vertices[r, q] for r, q in ids]
                ns = [radial[r, q]*sign for r, q in ids]
                uv = [(u*2*math.pi*radius/D.TILE, distance[r]/D.TILE)
                      for (r, _), u in zip(ids, (j/D.SIDES, (j+1)/D.SIDES, (j+1)/D.SIDES, j/D.SIDES))]
                D.face(model, pts, np.mean(ns, axis=0), D.IRON, uv, ns)
    D.annulus(model, rings[0][0], rings[1][0], -tangents[0], D.IRON)
    D.annulus(model, rings[0][-1], rings[1][-1], tangents[-1])


def warehouse_path(bottom):
    points = [(0., 12., WAREHOUSE_TOP-bottom-10.1)]
    tangents = [(0., 0., -1.)]
    # Rounded offset around the seven-inch cornice. Both ends are vertical.
    for z in np.linspace(926., 908., 9):
        t = (z-908.)/18.
        y = 8.+4.*t*t*(3.-2.*t)
        slope = 4.*6.*t*(1.-t)/18.
        points.append((0., y, z-bottom))
        tangents.append(K.normalise((0., -slope, -1.)))
    points.append((0., 8., 8.))
    tangents.append((0., 0., -1.))
    for theta in np.linspace(0, math.radians(70), 9)[1:]:
        points.append((0., 8.+5.*(1-math.cos(theta)), 8.-5.*math.sin(theta)))
        tangents.append((0., math.sin(theta), -math.cos(theta)))
    points.append(np.asarray(points[-1])+np.asarray(tangents[-1])*3.)
    tangents.append(tangents[-1])
    return np.asarray(points), np.asarray(tangents)


def scupper(model, bottom):
    # Closed metal wall volume around an open U-channel; no fictitious cap
    # across the discharge. The small embedded end meets the solid wall.
    profile = np.array(((-2., 2.2), (-2., -.2), (2., -.2), (2., 2.2),
                        (1.8, 2.2), (1.8, 0.), (-1.8, 0.), (-1.8, 2.2)))
    rings = [np.array([(x, y, z+level-bottom) for x, z in profile])
             for y, level in ((-.18, 948.), (11.2, 946.2))]
    slope = (948.-946.2)/(11.2+.18)
    for i in range(len(profile)):
        j = (i+1) % len(profile)
        dx, dz = profile[j]-profile[i]
        outward = np.array((dz, -dx*slope, -dx))
        D.face(model, [rings[0][i], rings[1][i], rings[1][j], rings[0][j]], outward)
    for row, sign in ((0, -1), (1, 1)):
        for ids in ((0, 1, 6, 7), (1, 2, 5, 6), (2, 3, 4, 5)):
            D.face(model, [rings[row][i] for i in ids], (0, sign, 0), D.EDGE)


def warehouse(model, record):
    bottom = record['bottom']
    points, tangents = warehouse_path(bottom)
    pipe = K.Model()
    swept_pipe(pipe, points, tangents)
    append_local(model, pipe, record)
    head = K.Model()
    D.hopper(head, WAREHOUSE_TOP-bottom)
    append_local(model, head, record, (0, 7., 0))
    joints = np.arange(16., WAREHOUSE_TOP-bottom-20., 92.)
    sockets, brackets = K.Model(), K.Model()
    for z in joints:
        D.socket(sockets, z)
        D.bracket(brackets, L, z)
        # Extend only the hidden stand-off stem; wall plates stay at the wall.
        brackets.box((-.43, 2.60, z+1.25), (.43, 5.62, z+2.0), D.IRON)
    append_local(model, sockets, record, (0, 3., 0))
    append_local(model, brackets, record)
    feed = K.Model()
    scupper(feed, bottom)
    append_local(model, feed, record)
    return dict(path=points.tolist(), top=WAREHOUSE_TOP, lower_offset=8., upper_offset=12.)


def collect_gutters(records):
    gutters = []
    original = F.gutter
    def capture(model, module, e0, e1, n, height):
        outlets = [r['e'] for r in records if abs(r['top']-(height+.5)) < .01 and
                   e0 < r['e'] < e1 and abs(abs(r['n']-n)-2.8) < .01]
        assert len(outlets) == 2
        first = next(r for r in records if r['e'] == outlets[0] and abs(r['top']-(height+.5)) < .01 and
                     abs(abs(r['n']-n)-2.8) < .01)
        gutters.append(dict(e0=e0, e1=e1, n=n, height=height, outlets=sorted(outlets), direction=first['out'][1]))
    try:
        F.gutter = capture
        F.build(L)
    finally:
        F.gutter = original
    assert len(gutters) == 8
    return gutters


def gutter(model, record):
    e0, e1, n, height = (record[k] for k in ('e0', 'e1', 'n', 'height'))
    # The coping projects four inches. Place the gutter beyond that face,
    # rather than under the stone, and bridge it with a folded roof apron.
    n += record['direction']*4.
    angles = np.linspace(-math.pi, 0, 13)
    # Bias the cut slightly toward the outside lip so it discharges into the
    # inset hopper bowl, not behind its back wall.
    start, end = (5, 8) if record['direction'] > 0 else (4, 7)
    holes = [(e-2., e+2.) for e in record['outlets']]
    def p(e, radius, angle):
        return np.array((e, n+radius*math.cos(angle), height+radius*math.sin(angle)))
    for radius, inside in ((2.6, False), (2.32, True)):
        for index, (a, b) in enumerate(zip(angles, angles[1:])):
            intervals = [(e0, e1)]
            if start <= index < end:
                intervals = [(e0, holes[0][0]), (holes[0][1], holes[1][0]), (holes[1][1], e1)]
            normal = np.array((0, math.cos((a+b)/2), math.sin((a+b)/2)))*(-1 if inside else 1)
            for low, high in intervals:
                L.card(model, D.IRON, [p(low, radius, a), p(high, radius, a), p(high, radius, b), p(low, radius, b)], normal)
    # Keep the current end plates, rolled lips and support bands byte-matched
    # outside the pierced runs. The cut edges close the thickness of the shell.
    for e, sign in ((e0, -1), (e1, 1)):
        for a, b in zip(angles, angles[1:]):
            L.card(model, D.EDGE, [p(e, 2.6, a), p(e, 2.6, b), p(e, 2.32, b), p(e, 2.32, a)], (sign, 0, 0))
        L.card(model, D.IRON, [p(e, 2.32, a) for a in angles], (sign, 0, 0))
    for side in (-1, 1):
        L.bar(model, (e0, n+side*2.5, height), (e1, n+side*2.5, height), .28, D.EDGE, sides=6)
    for e in np.arange(e0+24, e1-12, 72):
        for a, b in zip(angles, angles[1:]):
            L.card(model, D.EDGE, [p(e-.5, 2.82, a), p(e+.5, 2.82, a), p(e+.5, 2.82, b), p(e-.5, 2.82, b)],
                   (0, math.cos((a+b)/2), math.sin((a+b)/2)))
        wall_n = record['n']-record['direction']*2.8
        a, b = sorted((wall_n-.10*record['direction'], wall_n+.26*record['direction']))
        model.box((e-1.5, a, height-2.2), (e+1.5, b, height+.25), D.IRON)
        a, b = sorted((wall_n+.22*record['direction'], wall_n+4.10*record['direction']))
        model.box((e-.43, a, height-.4), (e+.43, b, height+.4), D.IRON)
    for low, high in holes:
        for e, sign in ((low, 1), (high, -1)):
            for a, b in zip(angles[start:end], angles[start+1:end+1]):
                D.face(model, [p(e, 2.6, a), p(e, 2.6, b), p(e, 2.32, b), p(e, 2.32, a)], (sign, 0, 0))
        for angle, sign in ((angles[start], 1), (angles[end], -1)):
            tangent = np.array((0, -math.sin(angle), math.cos(angle)))*sign
            D.face(model, [p(low, 2.6, angle), p(high, 2.6, angle), p(high, 2.32, angle), p(low, 2.32, angle)], tangent)
    apron(model, record)


def apron(model, record):
    wall = record['n']-record['direction']*2.8
    direction = record['direction']
    height = record['height']
    # Top of the existing coping is height+6.5. The apron laps the original
    # .75-pitch roof and clears the stone, with a folded drip over the gutter.
    profile = np.array(((-8.5, 6.975), (4.25, 6.65), (5.25, 5.3),
                        (5.25, 5.2), (4.25, 6.55), (-8.5, 6.875)))
    rings = [np.array([(e, wall+direction*y, height+z) for y, z in profile])
             for e in (record['e0'], record['e1'])]
    for i in range(len(profile)):
        j = (i+1) % len(profile)
        dy, dz = profile[j]-profile[i]
        D.face(model, [rings[0][i], rings[1][i], rings[1][j], rings[0][j]], (0, -direction*dz, dy))
    for row, sign in ((0, -1), (1, 1)):
        for ids in ((0, 1, 4, 5), (1, 2, 3, 4)):
            D.face(model, [rings[row][i] for i in ids], (sign, 0, 0))


def build(records, gutters):
    old, new = K.Model(), K.Model()
    details = []
    for record in records:
        D.drainpipe(old, L, **record)
        if record['top'] < 400:
            modified = dict(record, top=record['top']-3.)
            D.drainpipe(new, L, **modified)
            details.append(dict(kind='shed', original=record, updated=modified))
        else:
            details.append(dict(kind='warehouse', original=record, updated=warehouse(new, record)))
    for record in gutters:
        F.gutter(old, L, *[record[k] for k in ('e0', 'e1', 'n', 'height')])
        gutter(new, record)
    L.configure(old)
    L.configure(new)
    return old, new, details


def stage(out):
    out = Path(out).resolve()
    assert not out.is_relative_to(K.ASSETS.resolve())
    out.mkdir(parents=True, exist_ok=True)
    baseline = json.loads((BASE/'manifest.json').read_text())
    assert all(D.sha(K.ROOT/p) == h for p, h in baseline['sources'].items())
    assert all(D.sha(K.ROOT/p) == h for p, h in baseline['protected'].items())
    records = baseline['layout']
    gutters = collect_gutters(records)
    old, new, details = build(records, gutters)
    W.validate_model(new)
    assert not new.boxes and not new.hulls
    for name, model in (('old', old), ('new', new)):
        K.write_obj(out/f'junctions-{name}.obj', model, F.MODEL)
    relative = 'models/maps/lowtide/lowtide_finish.obj'
    prior = BASE/'stage'/relative
    assert D.sha(prior) == baseline['changes'][relative]['after']
    before = prior.read_text()
    old_text, new_text = [(out/f'junctions-{v}.obj').read_text() for v in ('old', 'new')]
    result, removed = W.replace_faces(before, old_text, new_text)
    result = result.replace('# cast-frame-v2', f'# {REVISION}')
    assert W.face_keys(result, attributes=True) == W.face_keys(before, attributes=True)-W.face_keys(old_text, attributes=True)+W.face_keys(new_text, attributes=True)
    target = out/'stage'/relative
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result.encode())
    shutil.copy2(prior.with_suffix('.mtl'), target.with_suffix('.mtl'))
    materials = baseline['staged_material_changes']['files']
    for relative_material, h in materials.items():
        source = BASE/'stage'/relative_material
        assert D.sha(source) == h
        destination = out/'stage'/relative_material
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    sources = [Path(__file__), Path(D.__file__), Path(F.__file__), Path(L.__file__), Path(K.__file__), Path(W.__file__)]
    manifest = dict(revision=REVISION, production_changed=False, collision_changed=False, native_accepted=False,
                    baseline_manifest_sha256=D.sha(BASE/'manifest.json'), baseline_manifest=(BASE/'manifest.json').relative_to(K.ROOT).as_posix(),
                    sources={p.relative_to(K.ROOT).as_posix():D.sha(p) for p in sources}, protected=baseline['protected'],
                    gutters=gutters, drains=details, replaced_triangles=removed, new_triangles=new.triangle_count(),
                    delta_from_drain_candidate=new.triangle_count()-removed,
                    delta_from_live=baseline['delta_triangles']+new.triangle_count()-removed,
                    unchanged_triangles=sum(W.face_keys(before).values())-removed,
                    components={f'junctions-{v}.obj':D.sha(out/f'junctions-{v}.obj') for v in ('old', 'new')},
                    staged_files={p.relative_to(out/'stage').as_posix():D.sha(p) for p in (out/'stage').rglob('*') if p.is_file()},
                    live_before_sha256=baseline['changes'][relative]['before'],
                    inherited_materials=materials, canonical_generator_changed=False)
    assert all(D.sha(K.ROOT/p) == h for p, h in baseline['protected'].items())
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('revision', 'replaced_triangles', 'new_triangles', 'delta_from_live', 'unchanged_triangles')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
