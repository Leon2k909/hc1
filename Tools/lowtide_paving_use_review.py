"""CPU material/context review and numerical checks for the offline paving pass.

Reads exact saved architecture and the composed drainage candidate. Original
stone colour/PBR pixels remain unchanged. Clipped architecture is neutral;
this approximate renderer does not establish native appearance or performance.
"""
import argparse
import json
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

import lowtide_paving_use as U
import lowtide_warehouse_floor_review as F
import lowtide_concrete_wear_review as C
import lowtide_window_software as G
from lowtide_drain_context import clip
from lowtide_drain_review import materials as metal_materials
from lowtide_sack_preview import shadow_map

CASES = {
    'quay-shed': dict(origin=(1314., -1050., 0.), outward=(0., -1., 0.)),
    'warehouse-street': dict(origin=(1000., 207., 0.), outward=(1., 0., 0.)),
    'shed-wall-base': dict(origin=(1590., -1050., 0.), outward=(0., -1., 0.)),
}
VIEW = dict(eye=(.8, 1.8, 1.2), target=(0., .36, .13), scale=1.65, size=(1100, 820))
EXPOSURE = .78
FINISH = U.ROOT/'output/lowtide/quality-pass/drain-junctions/stage/models/maps/lowtide/lowtide_finish.obj'


def basis(case):
    out = np.asarray(case['outward'])
    return np.column_stack((np.cross(out, (0, 0, 1)), out, (0, 0, 1)))


def extract(path):
    positions, uvs, normals, paint = [], [], [], None
    outputs = {name: ([], []) for name in CASES}
    axes = {name: basis(case) for name, case in CASES.items()}
    lo, hi = np.array((-65., -6., -.1)), np.array((65., 110., 72.))
    with path.open() as stream:
        for line in stream:
            if line.startswith(('v ', 'vn ')):
                x, y, z = map(float, line.split()[1:])
                (positions if line.startswith('v ') else normals).append((-x, z, y))
            elif line.startswith('vt '):
                uvs.append(tuple(map(float, line.split()[1:3])))
            elif line.startswith('usemtl '):
                paint = line.split()[1]
            elif line.startswith('f '):
                refs = [tuple(int(v)-1 for v in token.split('/')) for token in line.split()[1:]]
                p = np.asarray([positions[i] for i, _, _ in refs])
                # Cheap world-space rejection avoids a matrix transform for most faces.
                for name, case in CASES.items():
                    delta = p-np.asarray(case['origin'])
                    if np.any(delta.min(axis=0) > 150) or np.any(delta.max(axis=0) < -150): continue
                    local = delta@axes[name]
                    if np.any(local.max(axis=0) < lo) or np.any(local.min(axis=0) > hi): continue
                    attrs = np.column_stack((local, [uvs[i] for _, i, _ in refs],
                                             np.asarray([normals[i] for _, _, i in refs])@axes[name]))
                    clipped = clip(attrs, lo, hi)
                    outputs[name][0].extend(clipped)
                    outputs[name][1].extend([paint]*len(clipped))
    return outputs


def maps():
    names = dict(color='materials/lowtide/lt_setts_color.png', normal='materials/lowtide/paving_relief/lt_setts_normal.png',
                 rough='materials/lowtide/lt_setts_rough.png', ao='materials/lowtide/paving_relief/lt_setts_ao.png',
                 height='materials/lowtide/paving_relief/lt_setts_height.png')
    result = {name: F.mips(U.ASSETS/path, name == 'color') for name, path in names.items()}
    result['use'] = F.mips(U.OUT/'stage'/U.MASK)
    return result, {path: U.sha(U.ASSETS/path) for path in names.values()}


def lookup(plan, settings):
    e0, e1, n0, n1 = settings['bounds_plan_inches']
    return np.stack(((plan[..., 0]-e0)/(e1-e0), (n1-plan[..., 1])/(n1-n0)), -1)


def eligible(plan, settings, height=0, normal_z=1):
    uv = lookup(plan, settings)
    return (np.abs(height) < .1) & (normal_z > .98) & np.all((uv >= 0) & (uv <= 1), axis=-1)


def paving(tri, pos, uv, attrs_dx, attrs_dy, case, data, settings, candidate, eye):
    region = np.array((.10351562, .06103516, .45751953, .50146484))
    scale = np.array((1.98078975, 1.50146056))
    repeat = np.column_stack((uv[:, 0], 1-uv[:, 1]))*scale
    rx = attrs_dx[3:5]*np.array((1, -1))*scale
    ry = attrs_dy[3:5]*np.array((1, -1))*scale
    dx, dy = np.broadcast_to(rx*region[2:], repeat.shape), np.broadcast_to(ry*region[2:], repeat.shape)
    def sample(name, at):
        return F.sample(data[name], region[:2]+np.mod(at, 1)*region[2:], dx, dy)
    view = F.unit(eye-pos)
    facing = np.maximum(view[:, 2], .01)
    repeat_vertices = np.column_stack((tri[:, 3], 1-tri[:, 4]))*scale
    gradient = np.linalg.solve(np.column_stack((tri[:, :2], np.ones(3))), repeat_vertices)
    fade = 1-U.smooth(300, 850, np.linalg.norm(eye-pos, axis=1))
    ray = view[:, :2]@gradient[:2]*.35433071*fade[:, None]/np.maximum(facing[:, None], .16)
    resolved = U.smooth(.35, 1.25, np.linalg.norm(ray/np.maximum(np.abs(rx)+np.abs(ry), .00001), axis=1))
    ray *= resolved[:, None]
    steps = np.rint(24-16*np.clip(facing, 0, 1)).astype(int)
    delta = ray/steps[:, None]
    depth = np.zeros(len(pos)); at = repeat.copy()
    surface = 1-sample('height', at)[:, 0]; previous = surface.copy()
    for _ in range(24):
        active = depth < surface
        if not active.any(): break
        previous[active] = surface[active]-depth[active]
        at[active] -= delta[active]; depth[active] += 1/steps[active]
        surface = 1-sample('height', at)[:, 0]
    after = surface-depth
    weight = np.clip(after/np.minimum(after-previous, -.00001), 0, 1)
    at += delta*weight[:, None]
    color = sample('color', at)
    raw = F.unit(sample('normal', at)*2-1)
    inv = np.linalg.inv(gradient[:2])
    tu, tv = (F.unit(np.r_[v, 0.]) for v in inv)
    normal = F.unit(raw[:, 0, None]*tu+raw[:, 1, None]*tv+raw[:, 2, None]*np.array((0, 0, 1)))
    rough = sample('rough', at)[:, 0]
    ao = sample('ao', at)[:, 0]
    absolute = pos@basis(case).T+case['origin']
    ground = np.column_stack((absolute[:, 1], -absolute[:, 0]))
    a = np.column_stack((ground[:, 0]*.80-ground[:, 1]*.60, ground[:, 0]*.60+ground[:, 1]*.80))
    b = np.column_stack((ground[:, 0]*.36+ground[:, 1]*.93, -ground[:, 0]*.93+ground[:, 1]*.36))
    patches = C.noise(a/270+13.7)*.48+C.noise(b/115+42.1)*.34+C.noise(ground/48+7.4)*.18
    wet = U.smooth(.31, .73, patches)
    use = np.zeros((len(pos), 3))
    if candidate:
        use_uv = lookup(absolute[:, :2], settings)
        p_dx, p_dy = attrs_dx[:3]@basis(case).T, attrs_dy[:3]@basis(case).T
        ax = lookup(absolute[:, :2]+p_dx[:2], settings)-use_uv
        ay = lookup(absolute[:, :2]+p_dy[:2], settings)-use_uv
        use = C.linear_mip(data['use'], use_uv, ax, ay)
        use *= eligible(absolute[:, :2], settings, absolute[:, 2])[:, None]
        wet = np.maximum(wet, use[:, 1]*.88)
    color *= (.91+.11*C.noise(ground/390+9))[:, None]
    color *= (1-.48*wet)[:, None]
    rough = rough*(1-wet)+np.maximum(.23, rough*.38)*wet
    grit = use[:, 0]*(.35+.65*(1-U.smooth(.72, .98, ao)))
    color *= 1+grit[:, None]*(np.array((.56, .51, .42))-1)
    rough = np.minimum(1, rough+grit*.05*(1-wet))
    return color, normal, rough, ao


def render(triangles, paints, shadows, material_data, mats, case, settings, candidate):
    eye, target = np.asarray(VIEW['eye'])/.0254, np.asarray(VIEW['target'])/.0254
    forward = F.unit(target-eye); right = F.unit(np.cross(forward, (0, 0, 1))); up = np.cross(right, forward)
    width, height = VIEW['size']; pixels = height/(VIEW['scale']/.0254)
    projected = triangles[..., :3]-eye
    screen = np.stack((width/2+projected@right*pixels, height/2-projected@up*pixels), -1)
    nearness = -projected@forward
    image = np.full((height, width, 3), .08, np.float32)
    depth_buffer = np.full((height, width), -1e8, np.float32)
    shadow, sr, su, minimum, span = shadows
    for tri, xy, near, paint in zip(triangles, screen, nearness, paints):
        geometric = F.unit(np.cross(tri[1, :3]-tri[0, :3], tri[2, :3]-tri[0, :3]))
        if geometric@(-forward) <= 0: continue
        lo = np.maximum(np.floor(xy.min(axis=0)).astype(int), 0)
        hi = np.minimum(np.ceil(xy.max(axis=0)).astype(int), (width-1, height-1))
        x0, y0 = lo; x1, y1 = hi
        if x1 < x0 or y1 < y0: continue
        (ax, ay), (bx, by), (cx, cy) = xy
        area = (bx-ax)*(cy-ay)-(by-ay)*(cx-ax)
        if abs(area) < 1e-9: continue
        x = np.arange(x0, x1+1)+.5; y = (np.arange(y0, y1+1)+.5)[:, None]
        a = ((bx-x)*(cy-y)-(by-y)*(cx-x))/area
        b = ((cx-x)*(ay-y)-(cy-y)*(ax-x))/area; c = 1-a-b
        z = a*near[0]+b*near[1]+c*near[2]
        depth = depth_buffer[y0:y1+1, x0:x1+1]
        visible = (a >= -1e-7) & (b >= -1e-7) & (c >= -1e-7) & (z > depth)
        if not visible.any(): continue
        weights = np.stack((a[visible], b[visible], c[visible]), -1)
        attrs = weights@tri; pos, uv = attrs[:, :3], attrs[:, 3:5]
        derivatives = np.linalg.solve(np.column_stack((xy, np.ones(3))), tri)
        if paint == 'setts':
            base, normal, rough, ao = paving(tri, pos, uv, derivatives[0], derivatives[1], case, material_data, settings, candidate, eye)
        else:
            m = mats.get(paint)
            normal = F.unit(attrs[:, 5:]); ao = np.ones(len(pos))
            if m is not None:
                incoming = np.column_stack((uv[:, 0], 1-uv[:, 1]))
                mapped = m['region'][:2]+np.mod(incoming*m['scale'], 1)*m['region'][2:]
                mapped[:, 1] = 1-mapped[:, 1]
                base = G.sample_texture(m['texture'], mapped); rough = np.full(len(pos), m['rough'])
            else:
                color = (.26, .18, .13) if 'brick' in paint else (.17, .21, .15) if 'door' in paint else (.30, .31, .30)
                base = np.tile(color, (len(pos), 1)); rough = np.full(len(pos), .83)
        sh_uv = (np.column_stack((pos@sr, pos@su))-minimum)/span*(shadow.shape[0]-1)
        sh_pixel = np.rint(sh_uv).astype(int); light = np.zeros(len(pos))
        denominator = geometric@G.SUN
        denominator = math.copysign(max(abs(denominator), .10), denominator)
        gradient = np.array((geometric@sr, geometric@su))/denominator
        for ox, oy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            sx = np.clip(sh_pixel[:, 0]+ox, 0, shadow.shape[1]-1)
            sy = np.clip(sh_pixel[:, 1]+oy, 0, shadow.shape[0]-1)
            delta = (np.column_stack((sx, sy))-sh_uv)/(shadow.shape[0]-1)*span
            receiver = pos@G.SUN-delta@gradient
            light += (receiver >= shadow[sy, sx]-.035)/5
        diffuse = np.maximum(normal@G.SUN, 0)*light
        sky = .26+.16*np.clip(normal[:, 2], -1, 1)
        lit = base*(sky[:, None]*np.array((.82, .90, 1.))*ao[:, None]+diffuse[:, None]*2.4)
        half = F.unit(G.SUN+F.unit(eye-pos))
        exponent = np.maximum(8, 2/np.maximum(rough, .1)**4-2)
        spec = np.maximum(np.sum(normal*half, axis=1), 0)**exponent*light*.10
        image[y0:y1+1, x0:x1+1][visible] = lit+spec[:, None]
        depth[visible] = z[visible]
    hdr = image*EXPOSURE
    rgb = np.clip((hdr*(2.51*hdr+.03))/(hdr*(2.43*hdr+.59)+.14), 0, 1)
    rgb = np.where(rgb <= .0031308, rgb*12.92, 1.055*rgb**(1/2.4)-.055)
    result = Image.fromarray(np.rint(rgb*255).astype(np.uint8))
    draw = ImageDraw.Draw(result)
    draw.rectangle((0, height-28, width, height), fill=(22, 25, 26))
    draw.text((12, height-20), 'OFFLINE CONTEXT | '+('CANDIDATE PAVING USE' if candidate else 'CURRENT PAVING')+
              ' | same staged drain, neutral walls; approximate CPU light, not engine acceptance', fill=(225, 225, 218))
    return result


def verify(manifest):
    if 'project_root' in manifest:
        assert Path(manifest['project_root']).resolve() == U.ROOT, 'Candidate belongs to another checkout'
    assert all(U.sha(U.ROOT/p) == digest for p, digest in manifest['sources'].items())
    assert all(U.sha(U.ROOT/p) == digest for p, digest in manifest['protected'].items())
    assert all(U.sha(U.OUT/'stage'/p) == digest for p, digest in manifest['staged_files'].items())
    assert U.shader() == (U.OUT/'stage'/U.SHADER).read_text(), 'Staged shader no longer matches the reversible current-source edit'
    data = np.asarray(Image.open(U.OUT/'stage'/U.MASK))
    settings = manifest['settings']
    domain = U.domain_mask(manifest['ground'], settings)
    assert np.all(data[~domain] == 0)
    assert not data[[0, -1]].any() and not data[:, [0, -1]].any()
    assert np.array_equal(data[..., 2] > 0, domain)
    assert np.all(data[..., :2] <= data[..., 2, None])
    rng = np.random.default_rng(5215)
    ids = rng.choice(np.flatnonzero(domain), 12000, replace=False)
    y, x = np.unravel_index(ids, domain.shape)
    e0, e1, n0, n1 = settings['bounds_plan_inches']; w, h = settings['atlas_pixels']
    plan = np.stack((e0+(x+.5)/w*(e1-e0), n1-(y+.5)/h*(n1-n0)), -1)
    coordinates = lookup(plan, settings)
    assert np.allclose(coordinates, np.stack(((x+.5)/w, (y+.5)/h), -1), atol=1e-13)
    assert eligible(plan, settings).all()
    for z, nz in ((.1, 1), (-.1, 1), (5, 1), (176, 1), (0, .98), (0, 0), (0, -1)):
        assert not eligible(plan[:32], settings, z, nz).any()
    outside = np.array(((e0-1, 0), (e1+1, 0), (0, n0-1), (0, n1+1)))
    assert not eligible(outside, settings).any()
    # Each nonzero moisture texel lies in a recorded outlet's local footprint.
    moisture_points = np.column_stack(np.where(data[..., 1] > 0))
    points = np.stack((e0+(moisture_points[:, 1]+.5)/w*(e1-e0), n1-(moisture_points[:, 0]+.5)/h*(n1-n0)), -1)
    covered = np.zeros(len(points), bool)
    for drain in manifest['drains']:
        if not drain['eligible_height']: continue
        delta = points-np.asarray(drain['position'])[:2]; direction = np.asarray(drain['out'])[:2]
        along = delta@direction; across = delta@np.array((-direction[1], direction[0]))
        radius = np.sqrt(((along-7)/settings['moisture_length_inches'])**2+(across/settings['moisture_width_inches'])**2)
        covered |= (radius < 1) & (along > -13)
    assert covered.all()
    return dict(status='offline_scope_and_material_data_passed', manifest_sha256=U.sha(U.OUT/'manifest.json'),
                reviewer_sha256=U.sha(Path(__file__)), atlas_samples=len(plan), excluded_surface_samples=7*32+4,
                moisture_texels_checked=len(points), drain_outlets_over_setts=sum(d['domain_samples'] > 0 for d in manifest['drains']),
                staged_files=len(manifest['staged_files']), protected_live_files=len(manifest['protected']),
                live_files_unchanged=True, base_pbr_and_relief_retained=True, native_compilation=False,
                limitation='CPU scope/data checks do not establish shader compilation, native appearance or performance')


def main(previews=True):
    manifest = json.loads((U.OUT/'manifest.json').read_text())
    report = verify(manifest)
    U.write(U.OUT/'verification.json', json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2), flush=True)
    if not previews: return
    preview = U.OUT/'preview'; preview.mkdir(parents=True, exist_ok=True)
    architecture = U.ASSETS/'models/maps/lowtide/lowtide_east.obj'
    structures, drains = extract(architecture), extract(FINISH)
    data, texture_hashes = maps()
    mats = metal_materials(U.ROOT/'output/lowtide/quality-pass/drain-construction', True)
    G.SUN = F.unit(np.array((-.5, .8, 1.)))
    for name, case in CASES.items():
        triangles = np.asarray(structures[name][0]+drains[name][0])
        paints = structures[name][1]+drains[name][1]
        assert 'setts' in paints
        shadows = shadow_map(triangles)
        for candidate in (False, True):
            label = 'candidate' if candidate else 'before'
            render(triangles, paints, shadows, data, mats, case, manifest['settings'], candidate).save(preview/f'{name}-{label}.png')
            print(f'Rendered {name} {label}', flush=True)
    provenance = dict(kind='Matched CPU material/context views', native_engine_capture=False,
                      manifest_sha256=U.sha(U.OUT/'manifest.json'), renderer_sha256=U.sha(Path(__file__)),
                      source_geometry={p.relative_to(U.ROOT).as_posix():U.sha(p) for p in (architecture, FINISH)},
                      original_texture_inputs=texture_hashes, cases=CASES, view=VIEW, exposure=EXPOSURE,
                      renderer_dependencies={p:U.sha(U.ROOT/p) for p in (
                          'Tools/lowtide_warehouse_floor_review.py', 'Tools/lowtide_concrete_wear_review.py',
                          'Tools/lowtide_window_software.py', 'Tools/lowtide_drain_context.py',
                          'Tools/lowtide_drain_review.py', 'Tools/lowtide_sack_preview.py')},
                      same_staged_drains_in_both=True, architecture='Exact clipped saved triangles with neutral materials',
                      wetness_model='Current rotated three-octave PavingWetness; contact grit and outlet moisture added only in the candidate',
                      limitations=['Approximate CPU PBR, relief and mip filtering', 'Native lighting, shader compilation, compression, temporal filtering and performance untested'],
                      files={p.name:U.sha(p) for p in sorted(preview.glob('*.png'))})
    U.write(preview/'provenance.json', json.dumps(provenance, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify-only', action='store_true')
    parser.add_argument('--output', type=Path, default=U.OUT)
    args = parser.parse_args()
    U.OUT = args.output.resolve()
    assert U.OUT.is_relative_to(U.ROOT/'output/lowtide/quality-pass')
    main(not args.verify_only)
