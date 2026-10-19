"""Stage open cast-iron drainage outside Assets; never invoke the live writer.

The current finish generator supplies placements. Only its drainpipe triangles
are replaced in a saved OBJ copy; gutters, fixtures, materials and collision
remain unchanged. Geometry dimensions are inches, in map_kit plan coordinates.
"""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

import numpy as np
from PIL import Image

import map_kit as K
import lowtide_finish as F
import lowtide_window_construction as W

REVISION = 'open-cast-drainage-v3'
SIDES = 16
TILE = 36.
IRON, EDGE = 'lt_drain_iron', 'lt_drain_edge'
SHADER = K.ROOT/'Sources/Lowtide/drainage/finish-metal.shader'


def stage_materials(out):
    """Correct the padded scan for the two existing drainage material slots."""
    source = K.ROOT/'Tools/lowtide_bridge_steel_source.png'
    color = K.ASSETS/'materials/lowtide/lt_bridge_steel_color.png'
    original, packed = [np.asarray(Image.open(p).convert('RGB')) for p in (source, color)]
    h, w = original.shape[:2]
    ph, pw = packed.shape[:2]
    assert np.array_equal(original, packed[:h, :w]), 'Scan pixels differ from the packed atlas'
    assert np.array_equal(packed[:, w:], np.repeat(packed[:, w-1:w], pw-w, axis=1))
    assert np.array_equal(packed[h:], np.repeat(packed[h-1:h], ph-h, axis=0))
    region = (.5/pw, .5/ph, (w-1)/pw, (h-1)/ph)
    files, changes = {}, {}
    shader_path = out/'stage/shaders/hc1_lowtide_finish_metal.shader'
    shader_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SHADER, shader_path)
    files[shader_path.relative_to(out/'stage').as_posix()] = sha(shader_path)
    for paint in (IRON, EDGE):
        live = K.ASSETS/f'materials/lowtide/finish/{paint}.vmat'
        params = dict(re.findall(r'(\w+)\s+"([^\"]+)"', live.read_text()))
        tint = ' '.join(params['g_vColorTint'].strip('[]').split()[:3])
        rough = params['TextureRoughness'].strip('[]').split()[0]
        material = f'''// Offline candidate: repeat only the original steel scan region.
"Layer0"
{{
    shader "shaders/hc1_lowtide_finish_metal.shader"
    F_SPECULAR "1"
    TextureColor "{params['TextureColor']}"
    TextureNormal "{params['TextureNormal']}"
    g_flTintColor "[{tint}]"
    g_vFinishRegion "[{' '.join(f'{v:.12f}' for v in region)}]"
    g_flFinishScale "1.5"
    g_flFinishRoughness "{rough}"
    g_flFinishMetalness "{params['g_flMetalness']}"
}}
'''
        relative = live.relative_to(K.ASSETS).as_posix()
        target = out/'stage'/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(material.encode())
        files[relative] = sha(target)
        changes[relative] = dict(before=sha(live), after=sha(target))
    return dict(files=files, changes=changes, source_region=region, source_size=[w, h],
                uv_repeat_scale=1.5, physical_tile_inches=24.,
                atlas_size=[pw, ph], source_pixels_preserved=True,
                scope='Existing iron/edge slots also serve gutters, grates and anchors in lowtide_finish.',
                native_shader_compilation=False)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def face(model, points, towards, paint=IRON, uv=None, normals=None):
    points = np.asarray(points, float)
    if np.dot(np.cross(points[1]-points[0], points[2]-points[0]), towards) < 0:
        points = points[::-1]
        if uv is not None: uv = uv[::-1]
        if normals is not None: normals = normals[::-1]
    model.polygon(paint, list(points), uv=uv, normals=normals)


def loft(model, rings, *, inside=False, paint=IRON):
    """A continuous wrap; circumference smooth, casting profile corners crisp."""
    rings = np.asarray(rings)
    count = rings.shape[1]
    vertical = np.r_[0., np.cumsum(np.mean(np.linalg.norm(np.diff(rings, axis=0), axis=2), axis=1))]
    around = [np.r_[0., np.cumsum(np.linalg.norm(np.roll(ring, -1, axis=0)-ring, axis=1))] for ring in rings]
    for row in range(len(rings)-1):
        along = rings[row+1]-rings[row]
        normals = []
        for r in (row, row+1):
            tangent = np.roll(rings[r], -1, axis=0)-np.roll(rings[r], 1, axis=0)
            ns = np.cross(tangent, along) * (-1 if inside else 1)
            ns /= np.linalg.norm(ns, axis=1, keepdims=True)
            normals.append(ns)
        for j in range(count):
            k = (j+1) % count
            points = [rings[row, j], rings[row, k], rings[row+1, k], rings[row+1, j]]
            ns = [normals[0][j], normals[0][k], normals[1][k], normals[1][j]]
            uv = [(around[row][j]/TILE, vertical[row]/TILE),
                  (around[row][j+1]/TILE, vertical[row]/TILE),
                  (around[row+1][j+1]/TILE, vertical[row+1]/TILE),
                  (around[row+1][j]/TILE, vertical[row+1]/TILE)]
            for ids in ((0, 1, 2), (0, 2, 3)):
                face(model, [points[i] for i in ids], np.mean([ns[i] for i in ids], axis=0),
                     paint, [uv[i] for i in ids], [ns[i] for i in ids])


def annulus(model, outer, inner, normal, paint=EDGE):
    # Plane coordinates prevent collapsed UVs on horizontal lips and open ends.
    normal = K.normalise(np.asarray(normal, float))
    a = K.normalise(np.cross(normal, (1., 0., 0.)))
    b = np.cross(normal, a)
    for j in range(len(outer)):
        k = (j+1) % len(outer)
        pts = [outer[j], outer[k], inner[k], inner[j]]
        uv = [(float(p@a)/TILE, float(p@b)/TILE) for p in pts]
        face(model, pts, normal, paint, uv)


def round_ring(z, radius, centre=(0., 5.)):
    t = np.linspace(0, 2*math.pi, SIDES, endpoint=False)
    return np.column_stack((centre[0]+radius*np.cos(t), centre[1]+radius*np.sin(t), np.full(SIDES, z)))


def socket(model, z):
    profile = ((0., 2.025), (.30, 2.48), (2.95, 2.48), (3.35, 2.19), (3.65, 2.19))
    outer = [round_ring(z+height, radius) for height, radius in profile]
    inner = [round_ring(z, 1.97), round_ring(z+3.65, 1.97)]
    loft(model, outer, paint=IRON)
    loft(model, inner, inside=True)
    annulus(model, outer[0], inner[0], (0, 0, -1), IRON)
    annulus(model, outer[-1], inner[-1], (0, 0, 1))


def pipe(model, height):
    # One continuous wall through the bend; both ends have open bores.
    points = [np.array((0., 5., height-10.1)), np.array((0., 5., 8.))]
    tangents = [np.array((0., 0., -1.))] * 2
    for theta in np.linspace(0, math.radians(70), 9)[1:]:
        points.append(np.array((0., 5.+5.*(1-math.cos(theta)), 8.-5.*math.sin(theta))))
        tangents.append(np.array((0., math.sin(theta), -math.cos(theta))))
    points.append(points[-1]+tangents[-1]*3.)
    tangents.append(tangents[-1])
    theta = np.linspace(0, 2*math.pi, SIDES, endpoint=False)
    normals = np.array([np.cos(theta)[:, None]*np.array((1., 0., 0.))+
                        np.sin(theta)[:, None]*np.cross(t, (1., 0., 0.)) for t in tangents])
    outer = np.asarray(points)[:, None, :]+normals*2.
    inner = np.asarray(points)[:, None, :]+normals*1.70
    # Normals derived from each bend chord give a shallow ridge at segment
    # boundaries. Explicit radial normals below keep the elbow shading smooth.
    for radius, rings, sign in ((2., outer, 1), (1.70, inner, -1)):
        distance = np.r_[0., np.cumsum(np.linalg.norm(np.diff(points, axis=0), axis=1))]
        for row in range(len(points)-1):
            for j in range(SIDES):
                k = (j+1) % SIDES
                ids = ((row, j), (row, k), (row+1, k), (row+1, j))
                pts = [rings[r, q] for r, q in ids]
                ns = [normals[r, q]*sign for r, q in ids]
                uv = [(u*2*math.pi*radius/TILE, distance[r]/TILE)
                      for (r, q), u in zip(ids, (j/SIDES, (j+1)/SIDES, (j+1)/SIDES, j/SIDES))]
                face(model, pts, np.mean(ns, axis=0), IRON, uv, ns)
    annulus(model, outer[0], inner[0], -tangents[0], IRON)
    annulus(model, outer[-1], inner[-1], tangents[-1])
    return dict(upper_centre=points[0].tolist(), outlet_centre=points[-1].tolist(),
                outlet_direction=tangents[-1].tolist(), bore_radius=1.70)


def hopper(model, height):
    t = np.linspace(0, 2*math.pi, SIDES, endpoint=False)
    def ring(z, width, depth, power):
        return np.column_stack((width*np.sign(np.cos(t))*abs(np.cos(t))**power,
                                5.+depth*np.sign(np.sin(t))*abs(np.sin(t))**power,
                                np.full(SIDES, height+z)))
    # Round spigot, flared square bowl, narrow rolled upper rim. No top cap.
    outer = [ring(*v) for v in ((-11., 2.14, 2.14, 1.), (-8.7, 2.14, 2.14, 1.),
                                (-2.1, 4.55, 3.85, .40), (-1.25, 4.55, 3.85, .40),
                                (-1.05, 4.92, 4.22, .40), (-.35, 4.92, 4.22, .40))]
    inner = [ring(*v) for v in ((-11., 1.78, 1.78, 1.), (-8.6, 1.78, 1.78, 1.),
                                (-1.95, 4.25, 3.55, .40), (-.35, 4.57, 3.87, .40))]
    loft(model, outer)
    loft(model, inner, inside=True)
    annulus(model, outer[0], inner[0], (0, 0, -1), IRON)
    annulus(model, outer[-1], inner[-1], (0, 0, 1))


def bracket(model, L, z):
    # A shallow cast wall plate, stand-off stem and two visible fixing heads.
    model.box((-1.5, -.10, z-.35), (1.5, .26, z+4.0), IRON)
    model.box((-.43, .22, z+1.25), (.43, 2.62, z+2.0), IRON)
    for height in (z+.30, z+3.35):
        L.bar(model, (0, .26, height), (0, .48, height), .25, EDGE, sides=6)
        # L.bar leaves its root open. Close it inside the wall plate so this
        # small fitting remains a manifold shell when inspected on its own.
        t = np.linspace(0, 2*math.pi, 6, endpoint=False)
        pts = [np.array((-.25*math.cos(a), .26, height+.25*math.sin(a))) for a in t]
        face(model, pts, (0, -1, 0), EDGE)


def drainpipe(model, L, e, n, top, out, bottom=3):
    height = float(top-bottom)
    local = K.Model()
    openings = pipe(local, height)
    hopper(local, height)
    joints = list(np.arange(16., height-20, 92.))
    for z in joints:
        socket(local, z)
        bracket(local, L, z)
    outward = np.asarray(out, float)
    assert np.isclose(np.linalg.norm(outward), 1) and outward[2] == 0
    basis = np.column_stack((np.cross(outward, (0, 0, 1)), outward, (0, 0, 1)))
    origin = np.array((e, n, bottom), float)
    for paint, faces in local.polygons.items():
        for index, (pts, normal) in enumerate(faces):
            ns = local.polygon_normals.get((paint, index))
            model.polygon(paint, [basis@p+origin for p in pts], basis@normal,
                          uv=local.polygon_uvs.get((paint, index)),
                          normals=[basis@v for v in ns] if ns is not None else None)
    F.configure(model)
    return dict(joints=len(joints), triangles=local.triangle_count(), openings=openings)


def collect(L):
    records = []
    original = F.drainpipe
    def capture(model, module, e, n, top, out, bottom=3):
        records.append(dict(e=e, n=n, top=top, out=list(out), bottom=bottom))
    try:
        F.drainpipe = capture
        F.build(L)  # Geometry in memory only; no asset/material/scene writer.
    finally:
        F.drainpipe = original
    assert len(records) == 36
    return records


def stage(out):
    import lowtide_map as L
    out = Path(out).resolve()
    assert not out.is_relative_to(K.ASSETS.resolve()), 'Offline outputs only'
    out.mkdir(parents=True, exist_ok=True)
    protected = {p.relative_to(K.ROOT).as_posix(): sha(p)
                 for folder in ('Assets/models/maps/lowtide', 'Assets/materials/lowtide', 'Assets/scenes/maps/Lowtide')
                 for p in (K.ROOT/folder).rglob('*') if p.is_file() and not p.name.endswith('_c')}
    records = collect(L)
    old, new = K.Model(), K.Model()
    details = []
    for record in records:
        F.drainpipe(old, L, **record)
        details.append(drainpipe(new, L, **record))
    L.configure(old)
    L.configure(new)
    W.validate_model(new)
    assert not new.boxes and not new.hulls
    for name, model in (('old', old), ('new', new)):
        K.write_obj(out/f'drains-{name}.obj', model, F.MODEL)
    live = K.ASSETS/'models/maps/lowtide/lowtide_finish.obj'
    text = live.read_text()
    before = out/'before'/live.name
    before.parent.mkdir(exist_ok=True)
    if before.exists(): assert sha(before) == sha(live), 'Production changed since this stage'
    else: shutil.copy2(live, before)
    old_text, new_text = [(out/f'drains-{v}.obj').read_text() for v in ('old', 'new')]
    result, removed = W.replace_faces(text, old_text, new_text)
    result = result.replace('# cast-frame-v2', f'# {REVISION}')
    expected = W.face_keys(text, attributes=True)-W.face_keys(old_text, attributes=True)+W.face_keys(new_text, attributes=True)
    assert W.face_keys(result, attributes=True) == expected
    target = out/'stage/models/maps/lowtide'/live.name
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(result.encode())
    shutil.copy2(live.with_suffix('.mtl'), target.with_suffix('.mtl'))
    for paint in new.polygons:
        assert f'from = "{paint}.vmat"' in live.with_suffix('.vmdl').read_text()
    material_stage = stage_materials(out)
    sources = [Path(__file__), Path(F.__file__), Path(L.__file__), Path(K.__file__), Path(W.__file__), SHADER,
               K.ROOT/'Tools/lowtide_bridge_steel_source.png',
               K.ASSETS/'materials/lowtide/lt_bridge_steel_color.png',
               K.ASSETS/'materials/lowtide/lt_bridge_steel_normal.png',
               *(K.ASSETS/f'materials/lowtide/finish/{v}.vmat' for v in (IRON, EDGE))]
    manifest = dict(revision=REVISION, production_changed=False, materials_changed=False,
                    staged_material_changes=material_stage,
                    collision_changed=False, new_material_slots=0, canonical_generator_changed=False,
                    protected=protected, sources={p.relative_to(K.ROOT).as_posix():sha(p) for p in sources},
                    layout=records, details=details, removed_triangles=removed,
                    candidate_triangles=new.triangle_count(), delta_triangles=new.triangle_count()-removed,
                    unchanged_triangles=sum(W.face_keys(text).values())-removed,
                    changes={live.relative_to(K.ASSETS).as_posix():dict(before=sha(live), after=sha(target))},
                    material_library=dict(source=live.with_suffix('.mtl').relative_to(K.ROOT).as_posix(),
                                          staged=target.with_suffix('.mtl').relative_to(out).as_posix(),
                                          sha256=sha(target.with_suffix('.mtl'))),
                    components={f'drains-{v}.obj':sha(out/f'drains-{v}.obj') for v in ('old', 'new')})
    assert all(sha(K.ROOT/p) == h for p, h in protected.items())
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('revision', 'removed_triangles', 'candidate_triangles',
                                            'delta_triangles', 'unchanged_triangles')}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    stage(parser.parse_args().stage)
