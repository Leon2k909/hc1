"""Stage subtle, world-aligned far-field colour variation for Belltower's vista.

Only the C and D albedo maps change. Existing painted parcels, roads, trees,
kind/normal maps, terrain geometry and gameplay remain byte-for-byte intact.
The same deterministic 2D field is evaluated in world coordinates for both
zones. Broad variation is strongest across farmland and weaker in dense woods.

    python Tools/belltower_farfield_trial.py --preview-only
    python Tools/belltower_farfield_trial.py

Never write to the accepted Assets paths. Once compared offline, the separate
candidate materials can be natively imported and temporarily assigned in
Belltower's viewport for matching before/after captures.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ACCEPTED = ROOT / "Assets/materials/belltower/vista"
FOREST_MATERIAL = ROOT / "Assets/materials/belltower/forest/forest_trees.vmat"
OUT = ROOT / "output/belltower/quality/farfield-v3"
RESOURCE = "materials/belltower/vista/farfield-v3"
ZONE_SIZES = {'c': 34000.0, 'd': 92000.0}
TOWN = (-2380.0, 2380.0, -1466.0, 1800.0)


def sha(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def hash_field(ix, iy, seed):
    """Coordinate-stable lattice hash; no numpy random sampling boundaries."""
    x = np.asarray(ix, dtype=np.int64)
    y = np.asarray(iy, dtype=np.int64)
    h = (x * 0x27D4EB2D ^ y * 0x165667B1 ^ seed * 0x9E3779B1) & 0xFFFFFFFF
    h ^= h >> 15
    h = (h * 0x2C1B3C6D) & 0xFFFFFFFF
    h ^= h >> 12
    h = (h * 0x297A2D39) & 0xFFFFFFFF
    h ^= h >> 15
    return h.astype(np.float32) / 4294967295.0


def noise(e, n, scale, seed):
    u, v = e / scale, n / scale
    ix, iy = np.floor(u).astype(np.int64), np.floor(v).astype(np.int64)
    fu, fv = u - ix, v - iy
    fu, fv = fu * fu * (3 - 2 * fu), fv * fv * (3 - 2 * fv)
    a = hash_field(ix, iy, seed) * (1 - fu) + hash_field(ix + 1, iy, seed) * fu
    b = hash_field(ix, iy + 1, seed) * (1 - fu) + hash_field(ix + 1, iy + 1, seed) * fu
    return a * (1 - fv) + b * fv


def smoothstep(low, high, t):
    f = np.clip((t - low) / (high - low), 0.0, 1.0)
    return f * f * (3 - 2 * f)


def field(e, n):
    """Low-amplitude broad weather/soil variation shared across zones."""
    # Domain warp prevents visible aligned patches in the far hillside.
    warp_e = (noise(e, n, 10400.0, 19) - .5) * 950.0
    warp_n = (noise(e, n, 11500.0, 37) - .5) * 950.0
    x, y = e + warp_e, n + warp_n
    return (.36 * noise(x, y, 1450.0, 71)
            + .38 * noise(x, y, 3700.0, 83)
            + .26 * noise(x, y, 9100.0, 97) - .5) * 2.0


def process_tile(rgb, e, n, zone):
    """Modify only outdoor colour; no albedo category or terrain type moves."""
    original = rgb.astype(np.float32) / 255.0
    luminance = original @ np.array((.2126, .7152, .0722), dtype=np.float32)
    # Fields/pasture are brighter than the painted woodland floor. A small
    # amount remains in forest to vary crowns without changing their palette.
    crop_weight = smoothstep(.22, .45, luminance)
    # Preserve pale rock and roadways, where large patch variation looks dirty.
    crop_weight *= 1.0 - .65 * smoothstep(.68, .86, luminance)
    strength = .085 + .44 * crop_weight
    # Zone blend zones retain the accepted colour, avoiding mismatched LODs.
    edge_e = np.maximum(np.maximum(TOWN[0] - e, e - TOWN[1]), 0.0)
    edge_n = np.maximum(np.maximum(TOWN[2] - n, n - TOWN[3]), 0.0)
    distance = np.maximum(edge_e, edge_n)
    fade = smoothstep(7300.0, 10500.0, distance) if zone == 'c' else smoothstep(37500.0, 42500.0, distance)
    modulation = np.clip(1.0 + strength * field(e, n) * fade, .77, 1.23)
    # Multiply equally in linear light to preserve hue, then encode sRGB.
    linear = np.where(original <= .04045, original / 12.92, ((original + .055) / 1.055) ** 2.4)
    linear *= modulation[..., None]
    out = np.where(linear <= .0031308, linear * 12.92, 1.055 * np.power(np.maximum(linear, 0), 1/2.4) - .055)
    return np.uint8(np.rint(np.clip(out, 0, 1) * 255.0))


def render_zone(zone, preview_only=False):
    margin = ZONE_SIZES[zone]
    infile = ACCEPTED / f'vista_{zone}_color.jpg'
    with Image.open(infile) as f:
        original_full = f.convert('RGB')
    dimensions = original_full.size
    assert dimensions == (4096, 4096)
    if preview_only:
        original = np.asarray(original_full.resize((1024, 1024), Image.Resampling.BOX))
    else:
        original = np.asarray(original_full)
    size = original.shape[0]
    span_e = TOWN[1] - TOWN[0] + margin * 2
    span_n = TOWN[3] - TOWN[2] + margin * 2
    east = TOWN[0] - margin + (np.arange(size) + .5) / size * span_e
    north = TOWN[3] + margin - (np.arange(size) + .5) / size * span_n
    result = np.empty_like(original)
    for start in range(0, size, 128):
        end = min(start + 128, size)
        ee, nn = np.meshgrid(east, north[start:end])
        result[start:end] = process_tile(original[start:end], ee, nn, zone)
    filename = f'vista_{zone}_color.jpg'
    if not preview_only:
        Image.fromarray(result, 'RGB').save(OUT / filename, quality=95, subsampling=0)
    view_size = 700
    before = Image.fromarray(original).resize((view_size, view_size), Image.Resampling.LANCZOS)
    after = Image.fromarray(result).resize((view_size, view_size), Image.Resampling.LANCZOS)
    sheet = Image.new('RGB', (view_size * 2, view_size + 32), '#182026')
    sheet.paste(before, (0, 32))
    sheet.paste(after, (view_size, 32))
    draw = ImageDraw.Draw(sheet)
    draw.text((12, 9), f'Existing landscape zone {zone.upper()}', fill='white')
    draw.text((view_size + 12, 9), 'Natural-field patina v3', fill='white')
    sheet.save(OUT / f'compare-{zone}.jpg', quality=88)
    old_l = np.asarray(before).astype(np.float32)
    new_l = np.asarray(after).astype(np.float32)
    return {'zone': zone, 'mean_absolute_difference_8bit': float(np.abs(new_l - old_l).mean()),
            'candidate_derived_from_accepted_color': sha(infile), 'dimensions': list(dimensions),
            'preview_only': preview_only}


def stage_materials():
    vista_source = ACCEPTED / 'vista_land.vmat'
    forest_source = FOREST_MATERIAL
    originals = {}
    for name, path in (('vista_land.vmat', vista_source), ('forest_trees.vmat', forest_source)):
        source = path.read_text(encoding='utf-8')
        for zone in 'cd':
            accepted = f'materials/belltower/vista/vista_{zone}_color.jpg'
            candidate = f'{RESOURCE}/vista_{zone}_color.jpg'
            assert source.count('"' + accepted + '"') == 1, (name, accepted)
            source = source.replace('"' + accepted + '"', '"' + candidate + '"')
        (OUT / name).write_text(source, encoding='utf-8', newline='\n')
        originals[path.relative_to(ROOT).as_posix()] = sha(path)
    paths = [OUT / f'vista_{zone}_color.jpg' for zone in 'cd'] + [OUT / n for n in ('vista_land.vmat', 'forest_trees.vmat')]
    records = []
    for path in paths:
        destination = ROOT / 'Assets' / RESOURCE / path.name
        if destination.exists() and sha(destination) != sha(path):
            raise ValueError(f'Conflicting staged resource {destination}')
        records.append({'path': f'{RESOURCE}/{path.name}', 'source': path.relative_to(ROOT).as_posix(),
                        'sha256': sha(path), 'expected_existing_sha256': sha(destination) if destination.exists() else None})
    sources = {p.relative_to(ROOT).as_posix(): sha(p) for p in (
        ACCEPTED / 'vista_c_color.jpg', ACCEPTED / 'vista_d_color.jpg',
        ACCEPTED / 'vista_land.vmat', FOREST_MATERIAL,
        ACCEPTED / 'vista_c_normal.jpg', ACCEPTED / 'vista_d_normal.jpg',
        ACCEPTED / 'vista_c_kind.png', ACCEPTED / 'vista_d_kind.png')}
    data = {'revision': 'farfield-v3', 'state': 'separate native comparison pending',
            'resources': records, 'accepted_inputs': sources, 'unchanged_normals_and_kinds': True,
            'modified_geometry_or_collision': False,
            'material_overrides': {
                'materials/belltower/vista/vista_land.vmat': f'{RESOURCE}/vista_land.vmat',
                'materials/belltower/forest/forest_trees.vmat': f'{RESOURCE}/forest_trees.vmat'},
            'file_hashes_preserved': originals}
    (OUT / 'manifest.json').write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
    return data


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--preview-only', action='store_true')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    summary = [render_zone(z, args.preview_only) for z in 'cd']
    if not args.preview_only:
        stage_materials()
    (OUT / ('preview-report.json' if args.preview_only else 'review-report.json')).write_text(
        json.dumps(summary, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
