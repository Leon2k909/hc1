"""Continuous timber and painted cast iron for the two Lowtide warehouses.

The generated colour scan is copied unchanged. The normal and roughness maps
encode shallow fibre relief. Existing model UVs run along each beam's long edge.
"""
import argparse
import json
from pathlib import Path
import shutil
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K

SOURCE = K.ROOT / 'Sources/Lowtide/structure'
RESOURCE = 'materials/lowtide/structure'
SHADER = 'shaders/hc1_lowtide_structure_v2.shader'
TIMBER = f'{RESOURCE}/lt_beam_timber_v2.vmat'
IRON = f'{RESOURCE}/lt_cast_iron_v2.vmat'


def numerical_maps(rgb):
    lum = rgb @ np.array([.2126, .7152, .0722], np.float32)
    height = (gaussian_filter(lum, 1.0, mode='wrap') - gaussian_filter(lum, 22, mode='wrap')) * .0012
    dx = (np.roll(height, -1, 1) - np.roll(height, 1, 1)) * rgb.shape[1] / (2 * .6)
    dy = (np.roll(height, -1, 0) - np.roll(height, 1, 0)) * rgb.shape[0] / (2 * 2.4)
    normal = np.stack([-dx, dy, np.ones_like(dx)], axis=2)
    normal /= np.linalg.norm(normal, axis=2, keepdims=True)
    rough = np.clip(.77 + (gaussian_filter(lum, 3, mode='wrap') - lum) * .6, .66, .9)
    return normal, rough


def material(prefix, tint, uv, floor, scale=1):
    return f'''"Layer0"
{{
    shader "{SHADER}"
    TextureColor "{prefix}_color.png"
    TextureNormal "{prefix}_normal.png"
    TextureRoughness "{prefix}_rough.png"
    TextureMetalness "materials/default/default_black_mask.tga"
    g_vStructureTint "[{tint}]"
    g_vStructureUvScale "[{uv}]"
    g_flStructureRoughnessScale "{scale}"
    g_flStructureRoughnessFloor "{floor}"
}}
'''


def write_materials(assets=None):
    assets = Path(assets) if assets is not None else K.ASSETS
    source = SOURCE / 'beam-timber-source.png'
    rgb = np.asarray(Image.open(source).convert('RGB'), np.float32) / 255
    normal, rough = numerical_maps(rgb)
    target = assets / RESOURCE
    target.mkdir(parents=True, exist_ok=True)
    (assets / SHADER).parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target / 'beam_timber_color.png')
    Image.fromarray(np.rint((normal * .5 + .5) * 255).clip(0, 255).astype(np.uint8)).save(target / 'beam_timber_normal.png')
    Image.fromarray(np.rint(rough * 255).astype(np.uint8)).save(target / 'beam_timber_rough.png')
    K.write_text(assets / SHADER, (SOURCE / 'structure-v2.shader').read_text())
    K.write_text(assets / TIMBER, material(f'{RESOURCE}/beam_timber', '.72 .70 .66', '1.354666667 .338666667', .7))
    # The marine paint scan already has correctly scaled chips and surface data.
    # This coating is dielectric: exposed rust is not reflective bare metal.
    K.write_text(assets / IRON, material('materials/lowtide/marine/paint', '1.15 1.15 1.15', '1.354666667 1.354666667', .55, .9))
    resources = [SHADER, TIMBER, IRON, *(f'{RESOURCE}/beam_timber_{name}.png' for name in ('color', 'normal', 'rough'))]
    for relative in resources:
        metadata = json.dumps({'guid': str(uuid.uuid5(uuid.NAMESPACE_URL, relative))}, indent=2) + '\n'
        K.write_text(Path(str(assets / relative) + '.meta'), metadata)
    return resources


def configure(model):
    """Call only on the east/west warehouse architecture models."""
    if not {'lt_timber', 'iron_black'}.issubset(model.polygons):
        raise ValueError('Expected Lowtide warehouse timber and iron slots')
    model.material_overrides['lt_timber'] = TIMBER
    model.material_overrides['iron_black'] = IRON


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True, help='Staged Assets directory')
    args = parser.parse_args()
    write_materials(args.output)
