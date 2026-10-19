"""Stage a ground-contact material pass without touching any live resource.

The RGB mask encodes grit, drain moisture and the actual setts surface domain.
It is numerical data, not a replacement or modification of generated artwork.
Wall feet and ground UVs come from the saved meshes. --current uses the canonical
drain construction; the legacy staging path retains its historical manifest.
This static art layout is not a rainfall/fluid simulation.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import uuid

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'Assets'
SOURCE = ROOT / 'Sources/Lowtide/paving'
OUT = ROOT / 'output/lowtide/quality-pass/paving-use'
JUNCTIONS = ROOT / 'output/lowtide/quality-pass/drain-junctions/manifest.json'
BASE_SHADER = ASSETS / 'shaders/hc1_lowtide_paving_relief.shader'
MATERIAL = 'materials/lowtide/lt_setts.vmat'
SHADER = 'shaders/hc1_lowtide_paving_use.shader'
MASK = 'materials/lowtide/paving-use/ground_use.png'
WALL_PAINTS = {'brick', 'lt_brick_soot', 'lt_brick_glazed', 'lt_arch_clay',
               'ashlar_grey', 'lt_granite_trim', 'lt_door_green', 'lt_door_red',
               'rw_concrete', 'rw_concrete_dark'}


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8', newline='\n')


def smooth(a, b, v):
    t = np.clip((v-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def saved_surfaces():
    ground, segments, sources = [], set(), {}
    for name in ('east', 'west', 'fleet', 'finish'):
        path = ASSETS / f'models/maps/lowtide/lowtide_{name}.obj'
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
        vertices, uv, paint = [], [], None
        with path.open() as stream:
            for line in stream:
                if line.startswith('v '):
                    x, y, z = map(float, line.split()[1:])
                    vertices.append((-x, z, y))
                elif line.startswith('vt '):
                    uv.append(tuple(map(float, line.split()[1:3])))
                elif line.startswith('usemtl '):
                    paint = line.split()[1]
                elif line.startswith('f ') and (paint == 'setts' or paint in WALL_PAINTS):
                    refs = [tuple(int(v)-1 for v in token.split('/')) for token in line.split()[1:]]
                    p = np.asarray([vertices[v] for v, _, _ in refs])
                    normal = np.cross(p[1]-p[0], p[2]-p[0])
                    normal /= max(float(np.linalg.norm(normal)), 1e-12)
                    if paint == 'setts':
                        assert np.max(np.abs(p[:, 2])) < .001 and normal[2] > .99
                        for i in range(1, len(p)-1):
                            ids = (0, i, i+1)
                            ground.append(dict(model=name, points=p[list(ids), :2].tolist(),
                                               uv=[uv[refs[j][1]] for j in ids]))
                    elif p[:, 2].min() <= 6 and p[:, 2].max() >= 18 and abs(normal[2]) < .02:
                        xy = np.unique(p[:, :2], axis=0)
                        delta = xy[:, None]-xy[None, :]
                        a, b = np.unravel_index(np.sum(delta*delta, axis=2).argmax(), (len(xy), len(xy)))
                        if np.linalg.norm(xy[a]-xy[b]) > 4:
                            pair = tuple(sorted((tuple(xy[a]), tuple(xy[b]))))
                            segments.add(pair)
    assert ground and segments
    return ground, [list(map(list, pair)) for pair in sorted(segments)], sources


def pixel(points, settings):
    e0, e1, n0, n1 = settings['bounds_plan_inches']
    w, h = settings['atlas_pixels']
    p = np.asarray(points)
    return np.stack(((p[..., 0]-e0)/(e1-e0)*w-.5, (n1-p[..., 1])/(n1-n0)*h-.5), -1)


def domain_mask(ground, settings):
    image = Image.new('L', tuple(settings['atlas_pixels']))
    draw = ImageDraw.Draw(image)
    for tri in ground:
        draw.polygon([tuple(p) for p in pixel(tri['points'], settings)], fill=255)
    return np.asarray(image) > 0


def noise(shape, sigma, seed):
    a = ndimage.gaussian_filter(np.random.default_rng(seed).normal(size=shape).astype(np.float32), sigma, mode='reflect')
    return np.clip(.5+a/max(float(a.std()), 1e-8)*.16, 0, 1)


def drain_outlets():
    manifest = json.loads(JUNCTIONS.read_text())
    result = []
    for index, record in enumerate(manifest['drains']):
        original = record['original']
        out = np.asarray(original['out'], float)
        basis = np.column_stack((np.cross(out, (0, 0, 1)), out, (0, 0, 1)))
        if record['kind'] == 'warehouse':
            local = np.asarray(record['updated']['path'][-1])
        else:
            local = np.array((0., 11.10897714572938, 2.275476466093452))
        position = basis@local+np.array((original['e'], original['n'], original['bottom']))
        result.append(dict(index=index, kind=record['kind'], position=position.tolist(), out=out.tolist(),
                           eligible_height=bool(0 < position[2] < 10)))
    return result


def current_drain_outlets():
    """Follow the installed construction writers without a historical OBJ bundle."""
    import lowtide_map as L
    import lowtide_finish as F
    import lowtide_drain_junctions as J
    import lowtide_drain_construction as D
    import map_kit as K

    result, shed_ends = [], {}
    for side in (-1, 1):
        for kind, values in F.drainage_layout(L, side):
            if kind != 'pipe':
                continue
            e, n, top, outward, bottom = values
            out = np.asarray(outward, float)
            basis = np.column_stack((np.cross(out, (0, 0, 1)), out, (0, 0, 1)))
            warehouse = top > 400
            if warehouse:
                local = J.warehouse_path(bottom)[0][-1]
            else:
                height = top-bottom-3
                if height not in shed_ends:
                    shed_ends[height] = np.asarray(D.pipe(K.Model(), height)['outlet_centre'])
                local = shed_ends[height]
            position = basis@local+(e, n, bottom)
            result.append(dict(index=len(result), kind='warehouse' if warehouse else 'shed',
                               position=position.tolist(), out=out.tolist(),
                               eligible_height=bool(0 < position[2] < 10)))
    return result


def contact_material(material, settings=None):
    """Add contact data while retaining the base material's relief/PBR settings."""
    settings = settings or json.loads((SOURCE/'edge-use.json').read_text())
    original = 'shader "shaders/hc1_lowtide_paving_relief.shader"'
    if material.count(original) != 1 or 'TexturePavingUse' in material:
        raise ValueError('Expected one unextended Lowtide relief material')
    material = material.replace(original, f'shader "{SHADER}"', 1)
    e0, e1, n0, n1 = settings['bounds_plan_inches']
    return material.replace('    TextureColor ',
        f'    TexturePavingUse "{MASK}"\n    g_flPavingUse "1"\n'
        f'    g_vPavingUseBounds "[{e0} {n0} {e1-e0} {n1-n0}]"\n    TextureColor ', 1)


def fields(ground, segments, outlets, settings):
    e0, e1, n0, n1 = settings['bounds_plan_inches']
    w, h = settings['atlas_pixels']
    step = ((n1-n0)/h, (e1-e0)/w)
    domain = domain_mask(ground, settings)
    walls = Image.new('L', (w, h)); draw = ImageDraw.Draw(walls)
    for segment in segments:
        draw.line([tuple(p) for p in pixel(segment, settings)], fill=255, width=1)
    wall_pixels = np.asarray(walls) > 0
    distance = ndimage.distance_transform_edt(~wall_pixels, sampling=step)
    medium = noise((h, w), (12/step[0], 12/step[1]), 17514)
    fine = noise((h, w), (2/step[0], 2/step[1]), 18514)
    grit = np.exp(-distance/settings['grit_decay_inches'])*(.35+.65*medium)*(.7+.3*fine)
    grit *= 1-smooth(settings['grit_cutoff_inches']*.65, settings['grit_cutoff_inches'], distance)
    moist = np.zeros((h, w), np.float32)
    yy, xx = np.mgrid[0:h, 0:w]
    east = e0+(xx+.5)*step[1]; north = n1-(yy+.5)*step[0]
    for drain in outlets:
        if not drain['eligible_height']:
            drain['domain_samples'] = 0
            continue
        position, direction = np.asarray(drain['position']), np.asarray(drain['out'])
        de, dn = east-position[0], north-position[1]
        along = de*direction[0]+dn*direction[1]
        across = -de*direction[1]+dn*direction[0]
        length = settings['moisture_length_inches']
        width = settings['moisture_width_inches']
        radius = np.sqrt(((along-7)/length)**2+(across/width)**2)
        patch = (1-smooth(.18, 1.0, radius))*(.64+.36*medium)*(.8+.2*fine)
        patch *= smooth(-13, -5, along)
        active = (patch > .05) & domain
        drain['domain_samples'] = int(active.sum())
        moist = np.maximum(moist, patch)
        grit = np.maximum(grit, patch*.26)
    data = np.stack((grit*domain, moist*domain, domain), -1)
    data[[0, -1]] = 0; data[:, [0, -1]] = 0
    return np.rint(np.clip(data, 0, 1)*255).astype(np.uint8), distance


def shader():
    base = BASE_SHADER.read_text()
    extension = (SOURCE / 'edge-use.hlsl').read_text()
    anchor = '    float4 MainPs( PixelInput input ) : SV_Target0'
    assert base.count(anchor) == 1
    text = base.replace(anchor, extension+'\n'+anchor, 1)
    old_wet = '        float wet = PavingWetness( ground );'
    new_wet = old_wet+'\n        float3 use = PavingUse( input, material.WorldPosition );\n        wet = max( wet, use.g * .88 );'
    assert text.count(old_wet) == 1
    text = text.replace(old_wet, new_wet, 1)
    old_ao = '        material.AmbientOcclusion = rma.b;'
    new_ao = ('        // Concentrate settled grit in existing joints without baking lighting into the data.\n'
              '        float joint = 1 - smoothstep( .72, .98, rma.b );\n'
              '        float grit = use.r * lerp( .35, 1.0, joint );\n'
              '        material.Albedo *= lerp( float3( 1, 1, 1 ), float3( .56, .51, .42 ), grit );\n'
              '        material.Roughness = min( 1, material.Roughness + grit * .05 * ( 1 - wet ) );\n'+old_ao)
    assert text.count(old_ao) == 1
    text = text.replace(old_ao, new_ao, 1)
    assert text.replace(extension+'\n', '', 1).replace(new_wet, old_wet, 1).replace(new_ao, old_ao, 1) == base
    return text


def build(out=OUT, baseline_audit=None):
    out = out.resolve()
    assert out.is_relative_to(ROOT / 'output/lowtide/quality-pass')
    settings = json.loads((SOURCE / 'edge-use.json').read_text())
    prior = json.loads(JUNCTIONS.read_text())
    protected = dict(prior['protected'])
    rebase = None
    if baseline_audit is not None:
        baseline_audit = Path(baseline_audit).resolve()
        assert baseline_audit.is_relative_to(ROOT/'output/lowtide/quality-pass')
        baseline = json.loads(baseline_audit.read_text())
        assert Path(baseline['project_root']).resolve() == ROOT, 'Audit belongs to another checkout'
        assert not (out/'manifest.json').exists(), 'Rebase into a new folder; preserve historical evidence'
        protected = {p:baseline['current_hashes'][p] for p in protected}
        for path in (BASE_SHADER, ASSETS/MATERIAL):
            rel = path.relative_to(ROOT).as_posix()
            protected[rel] = baseline['current_hashes'][rel]
        assert all(h is not None and sha(ROOT/p) == h for p, h in protected.items()), 'Checkout changed after its audit'
        # Moisture still belongs to the separate drainage candidate. Confirm its
        # input architecture and exported mesh instead of accepting stale hashes.
        finish = 'models/maps/lowtide/lowtide_finish.obj'
        assert sha(ASSETS/finish) == prior['live_before_sha256'], 'Rebuild drainage for the changed finish mesh first'
        for name in ('east', 'west'):
            rel = f'Assets/models/maps/lowtide/lowtide_{name}.obj'
            assert sha(ROOT/rel) == prior['protected'][rel], 'Drainage context geometry changed'
        assert all(sha(JUNCTIONS.parent/'stage'/p) == h for p, h in prior['staged_files'].items())
        rebase = dict(audit=baseline_audit.relative_to(ROOT).as_posix(), audit_sha256=sha(baseline_audit),
                      drainage_manifest_sha256=sha(JUNCTIONS), drainage_geometry_revalidated=True,
                      drainage_native_accepted=False, detected_changes=baseline['changed_paths'])
        for folder in ('Assets/models/maps/lowtide', 'Assets/materials/lowtide', 'Assets/scenes/maps/Lowtide'):
            for path in (ROOT/folder).rglob('*'):
                if path.is_file() and not path.name.endswith('_c'):
                    protected.setdefault(path.relative_to(ROOT).as_posix(), sha(path))
    for path in (BASE_SHADER, ASSETS / MATERIAL):
        protected.setdefault(path.relative_to(ROOT).as_posix(), sha(path))
    assert all(sha(ROOT/p) == digest for p, digest in protected.items())
    ground, segments, sources = saved_surfaces()
    ground_points = np.asarray([p for tri in ground for p in tri['points']])
    pixel_bounds = pixel(ground_points, settings)
    assert np.all(pixel_bounds > 1) and np.all(pixel_bounds < np.asarray(settings['atlas_pixels'])-2)
    outlets = drain_outlets()
    data, distance = fields(ground, segments, outlets, settings)
    stage = out / 'stage'
    (stage / MASK).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(data).save(stage / MASK)
    write(stage / SHADER, shader())
    material = contact_material((ASSETS / MATERIAL).read_text(), settings)
    write(stage / MATERIAL, material)
    for rel in (MASK, SHADER):
        write(Path(str(stage / rel)+'.meta'), json.dumps(dict(guid=str(uuid.uuid5(uuid.NAMESPACE_URL, rel))), indent=2)+'\n')
    for path in (Path(__file__), SOURCE/'edge-use.json', SOURCE/'edge-use.hlsl', JUNCTIONS, BASE_SHADER, ASSETS/MATERIAL):
        sources[path.relative_to(ROOT).as_posix()] = sha(path)
    assert all(sha(ROOT/p) == digest for p, digest in protected.items())
    domain = data[..., 2] > 0
    manifest = dict(revision=settings['revision'], status='offline_candidate_not_installed', production_changed=False,
                    project_root=str(ROOT), rebase=rebase,
                    settings=settings, sources=sources, protected=protected, ground=ground, wall_segments=segments,
                    drains=outlets, channels=['settled_grit', 'local_drain_moisture', 'existing_setts_domain'],
                    original_color_and_pbr_unchanged=True, base_shader_preserved_by_reversible_insertions=True,
                    delta_triangles=0, new_material_slots=0, model_remaps=0, extra_texture_lookups=1,
                    coverage_over_existing_setts=(data[domain, :2] > 25).mean(axis=0).tolist(),
                    staged_files={p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()},
                    live_before={p.relative_to(stage).as_posix():(sha(ASSETS/p.relative_to(stage)) if (ASSETS/p.relative_to(stage)).is_file() else None)
                                 for p in sorted(stage.rglob('*')) if p.is_file()},
                    native_accepted=False, canonical_generator_changed=False,
                    limitations=['Static surface-use layout, not a fluid simulation', 'Native shader compilation, visual response and performance are untested'])
    write(out/'manifest.json', json.dumps(manifest, indent=2)+'\n')
    print(json.dumps(dict(stage=str(stage), ground_triangles=len(ground), wall_segments=len(segments),
                         drains_over_setts=sum(d['domain_samples'] > 0 for d in outlets),
                         files=len(manifest['staged_files']), coverage=manifest['coverage_over_existing_setts']), indent=2))


def build_current(out):
    """Stage contact data after geometry changes, preserving installed PBR values."""
    out = Path(out).resolve()
    if not out.is_relative_to(ROOT/'output/lowtide/quality-pass') or (out/'manifest.json').exists():
        raise ValueError('Choose a new staging folder under output/lowtide/quality-pass')
    ground, segments, sources = saved_surfaces()
    settings = json.loads((SOURCE/'edge-use.json').read_text())
    outlets = current_drain_outlets()
    data, _ = fields(ground, segments, outlets, settings)
    material = (ASSETS/MATERIAL).read_text()
    if f'shader "{SHADER}"' in material:
        material = material.replace(f'shader "{SHADER}"', 'shader "shaders/hc1_lowtide_paving_relief.shader"', 1)
        material = re.sub(r'^    (?:TexturePavingUse|g_flPavingUse|g_vPavingUseBounds) .*\n', '', material, flags=re.M)
    stage = out/'stage'
    (stage/MASK).parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(data).save(stage/MASK)
    write(stage/SHADER, shader())
    write(stage/MATERIAL, contact_material(material, settings))
    for rel in (MASK, SHADER):
        current = Path(str(ASSETS/rel)+'.meta')
        text = current.read_text() if current.exists() else json.dumps(dict(guid=str(uuid.uuid5(uuid.NAMESPACE_URL, rel))), indent=2)+'\n'
        write(Path(str(stage/rel)+'.meta'), text)
    for p in (Path(__file__), SOURCE/'edge-use.json', SOURCE/'edge-use.hlsl', BASE_SHADER, ASSETS/MATERIAL):
        sources[p.relative_to(ROOT).as_posix()] = sha(p)
    if not all(sha(ROOT/p) == h for p, h in sources.items()):
        raise RuntimeError('Sources changed during staging')
    files = {p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()}
    result = dict(status='current_layout_staged_native_review_required', settings=settings, sources=sources,
                  ground_triangles=len(ground), wall_segments=len(segments), outlets=outlets,
                  drains_over_setts=sum(d['domain_samples'] > 0 for d in outlets),
                  staged_files=files, live_before={p:sha(ASSETS/p) if (ASSETS/p).is_file() else None for p in files},
                  production_changed=False, new_geometry=0, new_material_slots=0, extra_texture_lookups=1)
    write(out/'manifest.json', json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('ground_triangles', 'wall_segments', 'drains_over_setts')}))
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--baseline-audit', type=Path, help='Explicit current-checkout audit for rebasing into a new output folder')
    parser.add_argument('--current', action='store_true', help='Use current meshes and installed canonical drainage; stage into a new --output folder')
    args = parser.parse_args()
    if args.current:
        if args.baseline_audit:
            parser.error('--current and --baseline-audit select different staging workflows')
        build_current(args.output)
    else:
        build(args.output, args.baseline_audit)
