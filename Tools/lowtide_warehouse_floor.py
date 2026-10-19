"""Stage a separate scanned mezzanine floor material. Never writes live Assets.

The generated eight-board colour atlas is copied byte for byte. Numerical maps
describe shallow wood grain; board layout and supported joints are evaluated by
the candidate shader. All model geometry, collision and scene bytes are retained.
Native shader compilation, material appearance and cost remain unverified.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import uuid

import numpy as np
from PIL import Image
from scipy import ndimage, signal

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'Sources/Lowtide/floor'
OUT = ROOT / 'output/lowtide/quality-pass/warehouse-floor'
RESOURCE = 'materials/lowtide/warehouse-floor'
SHADER = 'shaders/hc1_lowtide_warehouse_floor.shader'
MATERIAL = f'{RESOURCE}/lt_warehouse_floor.vmat'
REVISION = 'scanned-warehouse-boards-v1'
TINT = (.62, .60, .56)
SHORT = (0, 3, 5, 7)
LONG = (1, 2, 4, 6)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding='utf-8', newline='\n')


def identify_rows(rgb):
    lum = rgb @ np.array((.2126, .7152, .0722))
    profile = ndimage.gaussian_filter1d(lum.mean(axis=1), 1)
    joints, _ = signal.find_peaks(-profile, prominence=.045, distance=len(profile)/10)
    if len(joints) != 7:
        raise ValueError(f'Expected seven horizontal gaps, got {joints.tolist()}')
    bounds = np.r_[0, joints, len(profile)-1]
    if np.max(np.abs(np.diff(bounds) - len(profile)/8)) > len(profile)*.014:
        raise ValueError('Scan board widths are not sufficiently consistent')
    # Sampling an inset strip avoids photographed grooves and source-image borders.
    # Pixel data are not moved, recoloured, resampled or painted over.
    margin = 10
    w, h = rgb.shape[1], rgb.shape[0]
    rects = [(12/w, (a+margin)/h, (w-24)/w, (b-a-2*margin)/h) for a, b in zip(bounds[:-1], bounds[1:])]
    return bounds.astype(int), rects


def numerical_maps(rgb, bounds, rects):
    h, w = rgb.shape[:2]
    lum = rgb @ np.array((.2126, .7152, .0722), dtype=np.float32)
    normal = np.zeros((h, w, 3), np.float32)
    normal[..., 2] = 1
    rough = np.ones((h, w), np.float32)*.79
    heights = []
    for row, (a, b) in enumerate(zip(bounds[:-1], bounds[1:])):
        b = h if row == 7 else b
        strip = lum[a:b]
        grain = strip - ndimage.gaussian_filter(strip, (1.4, 2.2), mode='nearest')
        relief = np.clip(ndimage.gaussian_filter(grain, .65)*.00065, -.00012, .00012)
        # Inset rectangle dimensions describe .254 m by one/two 2.794 m joist spans.
        metres_x = 2.794 * (1 if row in SHORT else 2)
        sx = metres_x / (rects[row][2]*w)
        sy = .254 / (rects[row][3]*h)
        gy, gx = np.gradient(relief, sy, sx)
        n = np.stack((-gx, gy, np.ones_like(gx)), -1)
        n /= np.linalg.norm(n, axis=-1, keepdims=True)
        normal[a:b] = n
        broad = strip - ndimage.gaussian_filter(strip, (7, 18), mode='nearest')
        rough[a:b] = np.clip(.79-grain*.18-broad*.08, .72, .87)
        heights.extend((float(relief.min()), float(relief.max())))
    return normal, rough, dict(relief_extrema_mm=[min(heights)*1000, max(heights)*1000],
        normal_max_tilt_degrees=float(np.degrees(np.arccos(normal[..., 2].min()))),
        roughness_range=[float(rough.min()), float(rough.max())])


def atlas_text(rects):
    lines = ['// Numerical layout of the unchanged generated scan.', 'float4 FloorAtlasRect( uint row )', '{']
    for i, rect in enumerate(rects):
        prefix = f'    if ( row == {i}u ) ' if i != 7 else '    '
        lines.append(prefix+'return float4( '+', '.join(f'{v:.10f}' for v in rect)+' );')
    return '\n'.join(lines+['}', ''])


def material_text():
    return f'''// Offline candidate: generated colour is copied unchanged.
"Layer0"
{{
    shader "{SHADER}"
    TextureColor "{RESOURCE}/warehouse_color.png"
    TextureNormal "{RESOURCE}/warehouse_normal.png"
    TextureRoughness "{RESOURCE}/warehouse_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vFloorTint "[{TINT[0]} {TINT[1]} {TINT[2]}]"
}}
'''


def protected_files():
    combined = json.loads((ROOT/'output/lowtide/quality-pass/construction-integration/manifest.json').read_text())
    result = dict(combined['protected'])
    for name in ('floorboards.vmat', 'floorboards_color.png', 'floorboards_normal.png', 'floorboards_rough.png'):
        rel = f'Assets/materials/buildings/{name}'
        result[rel] = sha(ROOT/rel)
    return result


def verify_floor_faces(path):
    verts, normals = [], []
    paint, faces = None, []
    for line in path.read_text().splitlines():
        parts = line.split()
        if not parts: continue
        if parts[0] == 'v': verts.append(tuple(map(float, parts[1:])))
        elif parts[0] == 'vn': normals.append(tuple(map(float, parts[1:])))
        elif parts[0] == 'usemtl': paint = parts[1]
        elif parts[0] == 'f' and paint == 'floorboards':
            refs = [list(map(int, token.split('/'))) for token in parts[1:]]
            points = [verts[r[0]-1] for r in refs]
            ns = [normals[r[2]-1] for r in refs]
            assert all(abs(p[1]-176)<1e-6 for p in points), points
            assert all(n == (0., 1., 0.) for n in ns), ns
            faces.append(points)
    assert len(faces) == 6, len(faces)
    return dict(triangles=len(faces), floor_height_inches=176, all_upward=True)


def build(out=OUT):
    out = out.resolve()
    if not out.is_relative_to(ROOT/'output/lowtide/quality-pass'):
        raise ValueError('This generator only writes to the offline quality-pass directory')
    guard = protected_files()
    assert all(sha(ROOT/p) == value for p, value in guard.items()), 'Production baseline changed; inspect before rebuilding'
    stage = out/'stage'
    textures = stage/RESOURCE
    textures.mkdir(parents=True, exist_ok=True)
    src = SOURCE/'warehouse-boards-source.png'
    rgb = np.asarray(Image.open(src).convert('RGB'), np.float32)/255
    assert min(rgb.shape[:2]) >= 1024
    bounds, rects = identify_rows(rgb)
    normal, rough, metrics = numerical_maps(rgb, bounds, rects)
    shutil.copy2(src, textures/'warehouse_color.png')
    Image.fromarray(np.rint((normal*.5+.5)*255).clip(0,255).astype(np.uint8)).save(textures/'warehouse_normal.png')
    Image.fromarray(np.rint(rough*255).clip(0,255).astype(np.uint8)).save(textures/'warehouse_rough.png')
    write(stage/MATERIAL, material_text())
    write(stage/SHADER, (SOURCE/'warehouse-floor.shader').read_text())
    write(stage/'shaders/hc1_lowtide_floor_atlas.hlsl', atlas_text(rects))
    models = {}
    for half in ('east', 'west'):
        relative = f'models/maps/lowtide/lowtide_{half}.vmdl'
        path = ROOT/'Assets'/relative
        before = path.read_bytes()
        old = b'{ from = "floorboards.vmat" to = "materials/buildings/floorboards.vmat" }'
        new = ('{ from = "floorboards.vmat" to = "'+MATERIAL+'" }').encode()
        assert before.count(old) == 1, relative
        target = stage/relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before.replace(old, new, 1))
        scope = verify_floor_faces(path.with_suffix('.obj'))
        models[relative] = dict(before=sha(path), after=sha(target), material_slot='floorboards.vmat', scope=scope)
    # Keep each existing VMDL identity; deterministic IDs only for genuinely new assets.
    for path in list(stage.rglob('*')):
        if path.is_file() and path.suffix in ('.shader', '.hlsl', '.vmat', '.png'):
            relative = path.relative_to(stage).as_posix()
            write(Path(str(path)+'.meta'), json.dumps({'guid':str(uuid.uuid5(uuid.NAMESPACE_URL,relative))},indent=2)+'\n')
    sources = {p.relative_to(ROOT).as_posix():sha(p) for p in (Path(__file__),src,SOURCE/'warehouse-floor.shader',SOURCE/'imagegen.json')}
    manifest = dict(revision=REVISION, status='offline_candidate_not_installed', production_changed=False,
        sources=sources, protected=guard, models=models, source_dimensions=list(rgb.shape[1::-1]),
        source_color_sha256=sha(src), staged_color_sha256=sha(textures/'warehouse_color.png'),
        board_bounds_pixels=bounds.tolist(), board_rectangles=rects,
        board_width_metres=.254, board_lengths_metres=[2.794,5.588],
        orientation='Along engine X (north), across the east/west joists',
        joint_support_north_inches=dict(first=440,spacing=110),
        numerical_surface_metrics=metrics,
        material_tint_linear=list(TINT),
        geometry_changes=0, collision_changes=0, scene_changes=0, new_material_slots=0,
        staged_files={p.relative_to(stage).as_posix():sha(p) for p in sorted(stage.rglob('*')) if p.is_file()},
        native_checks='Deferred; user requested offline work')
    assert all(sha(ROOT/p)==value for p,value in guard.items())
    write(out/'manifest.json', json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({k:manifest[k] for k in ('revision','source_dimensions','board_bounds_pixels','numerical_surface_metrics','geometry_changes','native_checks')},indent=2))
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=OUT)
    build(parser.parse_args().output)
