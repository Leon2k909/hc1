"""Railhead's curated CC0 surface scans and their reproducible import.

Only the Railhead material generator uses these. Original channel downloads are
cached in output/railhead/source-cache; generated game textures stay in Assets.
Run this file to prepare the scans before rebuilding railhead_materials.py.
"""
import hashlib
import json
import urllib.request
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'output/railhead/source-cache'
MANIFEST = Path(__file__).with_name('railhead_scanned_sources.json')
SOURCES = {
    'sandstone_blocks_05': ('4k', 'Rob Tuytel'),
    'old_sandstone_02': ('4k', 'Dimitrios Savva'),
    'rough_concrete': ('2k', 'Dimitrios Savva'),
    'blue_metal_plate': ('2k', 'Rob Tuytel'),
    'brown_planks_03': ('2k', 'Rob Tuytel'),
    'metal_plate_02': ('2k', 'Rob Tuytel'),
}
HEADERS = {'User-Agent': 'Railhead-asset-import/1.0'}


def request(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=HEADERS), timeout=40) as response:
        return response.read()


def prepare(asset):
    resolution, author = SOURCES[asset]
    records = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}
    if asset not in records:
        files = json.loads(request('https://api.polyhaven.com/files/' + asset))
        records[asset] = {
            'source': 'https://polyhaven.com/a/' + asset,
            'license': 'CC0-1.0',
            'license_url': 'https://polyhaven.com/license',
            'author': author,
            'resolution': resolution,
            'channels': {key: files[key][resolution]['png'] for key in ('Diffuse', 'nor_gl', 'arm')},
        }
        MANIFEST.write_text(json.dumps(records, indent=2) + '\n', encoding='utf-8')
    folder = CACHE / asset
    folder.mkdir(parents=True, exist_ok=True)
    for key, info in records[asset]['channels'].items():
        file = folder / (key + '.png')
        if file.exists():
            continue
        data = request(info['url'])
        if hashlib.md5(data).hexdigest() != info['md5']:
            raise ValueError('Source checksum mismatch: ' + asset + '/' + key)
        file.write_bytes(data)
        print('Imported ' + asset + '/' + key, flush=True)
    return folder


@lru_cache(maxsize=4)
def scan(asset):
    folder = prepare(asset)
    return tuple(np.asarray(Image.open(folder / (channel + '.png')).convert('RGB'), dtype=np.float32) / 255
                 for channel in ('Diffuse', 'nor_gl', 'arm'))


def resize(data, shape):
    h, w = shape
    image = Image.fromarray(np.clip(np.rint(data * 255), 0, 255).astype(np.uint8))
    return np.asarray(image.resize((w, h), Image.Resampling.LANCZOS), dtype=np.float32) / 255


def combine_normals(base, detail, strength):
    a, b = base * 2 - 1, detail * 2 - 1
    normal = np.dstack((a[..., 0] + b[..., 0] * strength,
                        a[..., 1] + b[..., 1] * strength,
                        a[..., 2] * np.maximum(b[..., 2], 0.15)))
    normal /= np.maximum(np.linalg.norm(normal, axis=-1, keepdims=True), 1e-5)
    return normal * 0.5 + 0.5


def concrete_detail(colours, rough, normal):
    colour, detail, packed = (resize(channel, rough.shape) for channel in scan('rough_concrete'))
    lum = colour.mean(axis=-1)
    # Retain the authored panel joints, ties and grime; the scan supplies mineral grain.
    grain = np.clip(lum / lum.mean(), 0.5, 1.55)
    colours = {key: value * (0.48 + 0.52 * grain)[..., None] for key, value in colours.items()}
    rough = np.clip(rough * 0.5 + packed[..., 1] * 0.5, 0.65, 1)
    normal = (combine_normals(normal * 0.5 + 0.5, detail, 0.28) * 2 - 1)
    return colours, rough, normal


def dressed_detail(colours, rough, normal):
    """Fine mineral pores beneath the trim's own courses and tooling marks."""
    source, detail, packed = scan('old_sandstone_02')
    h, w = source.shape[:2]
    # Inside a single block: transferring another set of mortar joints produces
    # overlapping courses, especially on the narrow pilasters and arch returns.
    region = (slice(int(h * .445), int(h * .545)), slice(int(w * .33), int(w * .70)))
    source, detail, packed = (resize(channel[region], rough.shape) for channel in (source, detail, packed))
    lum = source.mean(axis=-1)
    grain = np.clip(lum / ndimage.gaussian_filter(lum, 28), .74, 1.24)
    # This detail is high-pass and weak at the tile edges; the authored trim is seamless.
    y, x = np.indices(rough.shape)
    edge = np.minimum.reduce((x, y, rough.shape[1] - 1 - x, rough.shape[0] - 1 - y))
    weight = np.clip(edge / 48., 0, 1)
    colours = {key: value * (1 + .65 * (grain - 1) * weight)[..., None] for key, value in colours.items()}
    detail = detail * weight[..., None] + np.array((.5, .5, 1)) * (1 - weight[..., None])
    normal = combine_normals(normal * .5 + .5, detail, .18) * 2 - 1
    rough = np.clip(rough * .85 + packed[..., 1] * .15, .7, .98)
    return colours, rough, normal


def paint_detail(shape):
    colour, normal, packed = scan('blue_metal_plate')
    # Remove the scan's perimeter welds. The buffer has its own bevels and fixings.
    h, w = colour.shape[:2]
    region = (slice(int(h * .06), int(h * .94)), slice(int(w * .06), int(w * .94)))
    colour, normal, packed = (resize(channel[region], shape) for channel in (colour, normal, packed))
    lum = colour.mean(axis=-1)
    # A natural, nonuniform painted steel texture without transferring its blue paint.
    grain = np.clip(lum / ndimage.gaussian_filter(lum, 40), 0.45, 1.65)
    exposed = np.clip((0.16 - (colour[..., 2] - colour[..., 0])) * 9, 0, 1)
    exposed *= np.clip((lum - 0.16) * 3, 0, 1)
    return grain, normal, packed[..., 1], exposed


def contact_detail(shape):
    colour, normal, packed = scan('metal_plate_02')
    h, w = colour.shape[:2]
    # The inside of one weathered plate, without its square panel seams.
    region = (slice(int(h*.18), int(h*.42)), slice(int(w*.345), int(w*.496)))
    colour, normal, packed = (resize(channel[region], shape) for channel in (colour, normal, packed))
    lum = colour.mean(axis=-1)
    grain = np.clip(lum / np.median(lum), .4, 1.7)
    return grain, normal, packed[..., 1]


def write_surface(name, out_dir):
    """Return the usual material-generator result, or None for procedural surfaces."""
    assets = {'sandstone': 'old_sandstone_02', 'wood': 'brown_planks_03', 'sleeper': 'rough_concrete'}
    if name not in assets:
        return None
    colour, normal, packed = scan(assets[name])
    colour, normal, packed = colour.copy(), normal.copy(), packed.copy()
    paint = {'sandstone': 'rw_sandstone', 'wood': 'rw_wood', 'sleeper': 'rw_sleeper'}[name]
    if name == 'sandstone':
        # Warm, dressed station ashlar: retain the scan's fine pores and worn joints,
        # without the previous rubble-like relief or oversized blocks.
        colour *= np.array((.71, .65, .55), np.float32) / colour.mean(axis=(0, 1), dtype=np.float64)
        n = normal * 2 - 1
        n[..., :2] *= .72
        n /= np.maximum(np.linalg.norm(n, axis=-1, keepdims=True), 1e-5)
        normal = n * .5 + .5
        rough = np.clip(packed[..., 1] * .9 + .08, .72, .97)
    elif name == 'wood':
        # Warm the dry timber to match the varnished station benches, preserving its pores.
        colour *= np.array((1.32, .98, .69), np.float32)
        rough = np.clip(packed[..., 1] * .68, .4, .8)
    else:
        colour *= np.array((.82, .81, .78), np.float32)
        rough = np.maximum(packed[..., 1], .84)
    colour = np.clip(colour, 0, 1)
    out_dir.mkdir(parents=True, exist_ok=True)
    for file, data in ((paint + '_color', colour), (name + '_normal', normal),
                       (name + '_rough', rough), (name + '_ao', .65 + .35 * packed[..., 0])):
        Image.fromarray(np.clip(np.rint(data * 255), 0, 255).astype(np.uint8)).save(out_dir / (file + '.png'))
    resource = 'materials/railhead/'
    lines = ['// Tools/railhead_scanned.py; source and CC0 provenance in railhead_scanned_sources.json',
             '"Layer0"', '{', '    shader "shaders/complex.shader"', '    F_SPECULAR "1"',
             '    g_flMetalness "0"', '    g_flRoughnessScaleFactor "1"', '    g_vColorTint "[1 1 1 1]"',
             '    g_flModelTintAmount "1"', f'    TextureColor "{resource}{paint}_color.png"',
             f'    TextureNormal "{resource}{name}_normal.png"', f'    TextureRoughness "{resource}{name}_rough.png"',
             f'    TextureAmbientOcclusion "{resource}{name}_ao.png"', '}']
    (out_dir / (paint + '.vmat')).write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('Wrote scanned Railhead surface: ' + name, flush=True)
    return {paint: colour * 255}, normal * 2 - 1, {}


if __name__ == '__main__':
    for asset in SOURCES:
        prepare(asset)
