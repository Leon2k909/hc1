"""Matched CPU drainage views and exported-geometry checks; no engine access."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

import numpy as np
from PIL import Image, ImageDraw

import map_kit as K
import lowtide_map as L
import lowtide_finish as F
import lowtide_drain_construction as D
import lowtide_window_construction as W
import lowtide_window_software as R
from lowtide_sack_preview import shadow_map

VIEWS = {
    'shoe': dict(eye=(.65, 1.3, .62), target=(0., .13, .37), scale=.85, size=(800, 900)),
    'hopper': dict(eye=(.58, 1.2, 7.38), target=(0., .12, 6.90), scale=.56, size=(850, 800)),
    'fixing': dict(eye=(.43, .75, .70), target=(0., .12, .55), scale=.38, size=(850, 800)),
}


def materials(stage, corrected):
    result = {}
    for paint in (D.IRON, D.EDGE):
        folder = stage/'stage' if corrected else K.ASSETS
        text = (folder/f'materials/lowtide/finish/{paint}.vmat').read_text()
        inputs = dict(re.findall(r'(\w+)\s+"([^\"]+)"', text))
        rgb = np.asarray(Image.open(K.ASSETS/inputs['TextureColor']).convert('RGB'), np.float32)/255
        tex = np.where(rgb <= .04045, rgb/12.92, ((rgb+.055)/1.055)**2.4)
        tint = R.number_array(inputs['g_flTintColor'] if corrected else inputs['g_vColorTint'], [1, 1, 1])[:3]
        result[paint] = dict(texture=(tex*tint).astype(np.float32), scale=np.ones(2),
                             rough=float(inputs['g_flFinishRoughness']) if corrected else
                             float(R.number_array(inputs['TextureRoughness'], [.6])[0]))
        if corrected:
            result[paint]['region'] = R.number_array(inputs['g_vFinishRegion'], [0, 0, 1, 1])
            result[paint]['scale'] = np.repeat(float(inputs['g_flFinishScale']), 2)
    for name, color in (('review_wall', (.23, .25, .26)), ('review_ground', (.12, .13, .14))):
        result[name] = dict(texture=np.asarray([[color]], np.float32), scale=np.ones(2), rough=.8)
    return result


def review(out):
    out.mkdir(parents=True, exist_ok=True)
    R.SUN = K.normalise((-.5, .8, 1.))
    exports = {}
    frames = {}
    for label, build in (('before', F.drainpipe), ('mapping-only', F.drainpipe), ('candidate', D.drainpipe)):
        mats = materials(out.parent, label != 'before')
        model = K.Model()
        model.box((-22., -3., 0.), (22., 0., 282.), 'review_wall')
        model.box((-35., -6., -1.5), (35., 38., 0.), 'review_ground')
        model.tile_overrides.update(review_wall=36., review_ground=36.)
        build(model, L, 0, 0, 276., (0, 1, 0), 3.)
        F.configure(model)
        path = out/f'drain-{label}.obj'
        K.write_obj(path, model, F.MODEL)
        exports[path.name] = D.sha(path)
        triangles, paints = R.read_obj(path)
        for name, view in VIEWS.items():
            # Exclude distant geometry from the light's depth atlas; keep every
            # actual triangle that can cast within this isolated close view.
            target_z = view['target'][2]/.0254
            zlo, zhi = target_z-30., target_z+35.
            mask = (triangles[..., 2].max(axis=1) >= zlo) & (triangles[..., 2].min(axis=1) <= zhi)
            # The long wall box is retained in full, as is the pipe shaft.
            selected = triangles[mask]
            selected_paints = [p for p, keep in zip(paints, mask) if keep]
            result = R.render(selected, selected_paints, mats, shadow_map(selected), view)
            frames[(name, label)] = result
            result.save(out/f'{name}-{label}.png')
            print(f'Rendered {name}: {label}', flush=True)
    for name in VIEWS:
        before, after = frames[(name, 'before')], frames[(name, 'candidate')]
        sheet = Image.new('RGB', (before.width*2, before.height+56), (22, 24, 26))
        sheet.paste(before, (0, 30))
        sheet.paste(after, (before.width, 30))
        draw = ImageDraw.Draw(sheet)
        draw.text((15, 10), 'CURRENT GEOMETRY', fill=(235, 235, 230))
        draw.text((before.width+15, 10), 'OFFLINE CANDIDATE', fill=(235, 235, 230))
        draw.text((15, sheet.height-19), 'CPU preview | original scan pixels, corrected atlas sampling on candidate | native lighting and performance untested', fill=(200, 205, 210))
        sheet.save(out/f'{name}-comparison.png')
        sheet.paste(frames[(name, 'mapping-only')], (0, 30))
        draw.rectangle((0, 0, before.width, 29), fill=(22, 24, 26))
        draw.text((15, 10), 'CURRENT GEOMETRY WITH THE SAME MAPPING FIX', fill=(235, 235, 230))
        sheet.save(out/f'{name}-geometry-comparison.png')
    provenance = dict(native_engine_capture=False, geometry_generator_sha256=D.sha(D.__file__),
                      reviewer_sha256=D.sha(__file__), renderer_sha256=D.sha(R.__file__),
                      shadow_adapter_sha256=D.sha(K.ROOT/'Tools/lowtide_sack_preview.py'),
                      views=VIEWS, meshes=exports, manifest_sha256=D.sha(out.parent/'manifest.json'),
                      staged_materials={p.relative_to(out.parent/'stage').as_posix():D.sha(p)
                                        for p in (out.parent/'stage/materials').rglob('*.vmat')},
                      inputs={p.relative_to(K.ROOT).as_posix():D.sha(p) for p in (
                          K.ASSETS/'materials/lowtide/lt_bridge_steel_color.png',
                          *(K.ASSETS/f'materials/lowtide/finish/{p}.vmat' for p in (D.IRON, D.EDGE)))},
                      previews={p.name:D.sha(p) for p in out.glob('*.png')},
                      limitations=['Isolated drain geometry; gutter/roof junctions require map inspection.',
                                   'No engine metalness, normal mapping, GI, temporal rendering or performance check.'])
    (out/'provenance.json').write_text(json.dumps(provenance, indent=2)+'\n')


def intersections(triangles, origin, direction):
    p = triangles[..., :3]
    a, b = p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]
    h = np.cross(np.broadcast_to(direction, a.shape), b)
    det = np.einsum('ij,ij->i', a, h)
    hit = abs(det) > 1e-9
    inverse = np.divide(1., det, out=np.zeros_like(det), where=hit)
    s = np.asarray(origin)-p[:, 0]
    u = inverse*np.einsum('ij,ij->i', s, h)
    q = np.cross(s, a)
    v = inverse*(q@direction)
    distance = inverse*np.einsum('ij,ij->i', b, q)
    hit &= (u >= -1e-8) & (v >= -1e-8) & (u+v <= 1+1e-8) & (distance > 1e-7)
    return distance[hit]


def closed_mesh(triangles):
    edges = Counter()
    signed = Counter()
    p = triangles[..., :3]
    assert np.isfinite(triangles).all()
    area = np.linalg.norm(np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0]), axis=1)
    assert area.min() > 1e-6
    norms = triangles[..., 5:]
    assert np.max(abs(np.linalg.norm(norms, axis=2)-1)) < .000867
    uv = triangles[..., 3:5]
    du, dv = uv[:, 1]-uv[:, 0], uv[:, 2]-uv[:, 0]
    assert np.min(abs(du[:, 0]*dv[:, 1]-du[:, 1]*dv[:, 0])) > 1e-10
    for tri in p:
        for a, b in zip(tri, np.roll(tri, -1, axis=0)):
            a, b = tuple(a), tuple(b)
            key = tuple(sorted((a, b)))
            edges[key] += 1
            signed[key] += 1 if a < b else -1
    assert set(edges.values()) == {2}, Counter(edges.values())
    assert all(v == 0 for v in signed.values()), 'Inconsistent shell winding'
    return len(edges)


def verify(stage):
    manifest = json.loads((stage/'manifest.json').read_text())
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['protected'].items())
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['sources'].items())
    assert all(D.sha(stage/p) == h for p, h in manifest['components'].items())
    repro = K.Model()
    for record in manifest['layout']: D.drainpipe(repro, L, **record)
    L.configure(repro)
    dest = stage/'reproduction/drains-new.obj'
    dest.parent.mkdir(parents=True, exist_ok=True)
    K.write_obj(dest, repro, F.MODEL)
    assert D.sha(dest) == D.sha(stage/'drains-new.obj')
    whole, _ = R.read_obj(stage/'drains-new.obj')
    paired = closed_mesh(whole)
    # Inspect local examples in every source height. Straight sightlines through
    # the hopper throat and outlet end demonstrate that neither is falsely capped.
    aperture_samples = 0
    bounds = []
    heights = sorted({r['top']-r['bottom'] for r in manifest['layout']})
    for height in heights:
        model = K.Model()
        details = D.drainpipe(model, L, 0, 0, height, (0, 1, 0), 0)
        file = stage/f'verification/drain-{height}.obj'
        file.parent.mkdir(parents=True, exist_ok=True)
        K.write_obj(file, model, F.MODEL)
        tri, _ = R.read_obj(file)
        closed_mesh(tri)
        pts = tri[..., :3].reshape(-1, 3)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        assert lo[2] >= 0 and hi[2] <= height
        assert lo[1] >= -.101 and hi[1] <= 13.1
        assert lo[0] >= -4.93 and hi[0] <= 4.93
        bounds.append(dict(height=height, min=lo.tolist(), max=hi.tolist()))
        for radius in (0., .55, 1.25):
            for theta in np.linspace(0, 2*np.pi, 12, endpoint=False):
                offset = np.array((np.cos(theta), np.sin(theta), 0))*radius
                start = np.array((0., 5., height+1))+offset
                hits = intersections(tri, start, np.array((0., 0., -1.)))
                assert len(hits) and hits.min() > height-12, 'Hopper or vertical pipe bore capped'
                aperture_samples += 1
        info = details['openings']
        end, direction = np.asarray(info['outlet_centre']), np.asarray(info['outlet_direction'])
        a = np.array((1., 0., 0.))
        b = np.cross(direction, a)
        for radius in (0., .55, 1.25):
            for theta in np.linspace(0, 2*np.pi, 12, endpoint=False):
                start = end+direction*.5+radius*(np.cos(theta)*a+np.sin(theta)*b)
                hits = intersections(tri, start, -direction)
                assert len(hits) and hits.min() > 3.5, 'Outlet is capped or pinched'
                aperture_samples += 1
    original = (stage/'before/lowtide_finish.obj').read_text()
    old, new = [(stage/f'drains-{v}.obj').read_text() for v in ('old', 'new')]
    target = stage/'stage/models/maps/lowtide/lowtide_finish.obj'
    expected, _ = W.replace_faces(original, old, new)
    expected = expected.replace('# cast-frame-v2', f'# {D.REVISION}')
    assert target.read_text() == expected
    assert W.face_keys(target.read_text(), attributes=True) == W.face_keys(original, attributes=True)-W.face_keys(old, attributes=True)+W.face_keys(new, attributes=True)
    library = manifest['material_library']
    assert D.sha(K.ROOT/library['source']) == D.sha(stage/library['staged']) == library['sha256']
    material_stage = manifest['staged_material_changes']
    assert all(D.sha(stage/'stage'/p) == h for p, h in material_stage['files'].items())
    assert all(D.sha(K.ASSETS/p) == value['before'] for p, value in material_stage['changes'].items())
    # Exercise wraps, negative UVs and exact boundary cases in the shader's
    # normalized image space. Samples must stay inside the original source.
    rng = np.random.default_rng(61015)
    uv = np.vstack((rng.uniform(-100, 100, (20000, 2)), [[0, 0], [1, 1], [-1, -1], [1e-7, -1e-7]]))
    region = np.asarray(material_stage['source_region'])
    pixels = (region[:2]+np.mod(uv*material_stage['uv_repeat_scale'], 1)*region[2:])*np.array(material_stage['atlas_size'])-.5
    assert np.all(pixels >= -1e-9) and np.all(pixels <= np.array(material_stage['source_size'])-1+1e-9)
    assert np.array_equal(np.asarray(Image.open(K.ROOT/'Tools/lowtide_bridge_steel_source.png')),
                          np.asarray(Image.open(K.ASSETS/'materials/lowtide/lt_bridge_steel_color.png'))[:material_stage['source_size'][1], :material_stage['source_size'][0]])
    material_repro = D.stage_materials(stage/'reproduction')
    assert json.loads(json.dumps(material_repro)) == material_stage
    result = dict(status='offline_geometry_checks_passed', manifest_sha256=D.sha(stage/'manifest.json'),
                  verifier_sha256=D.sha(__file__), pipes=len(manifest['layout']), paired_edges=paired,
                  triangles=len(whole), aperture_ray_samples=aperture_samples,
                  unchanged_triangles=manifest['unchanged_triangles'], protected_live_files=len(manifest['protected']),
                  byte_identical_reproduced_components=1, atlas_mapping_samples=len(uv),
                  byte_identical_reproduced_material_files=len(material_stage['files']),
                  source_pixels_preserved=True, bounds=bounds, native_validation='Deferred')
    (stage/'verification.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', type=Path, required=True)
    parser.add_argument('--preview', action='store_true')
    args = parser.parse_args()
    assert not args.stage.resolve().is_relative_to(K.ASSETS.resolve())
    verify(args.stage)
    if args.preview: review(args.stage/'preview')
