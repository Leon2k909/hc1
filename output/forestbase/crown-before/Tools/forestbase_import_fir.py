"""Import checksum-verified CC0 firs and saplings with game LODs and cutout PBR.

Sources: https://polyhaven.com/a/fir_tree_01 and /a/fir_sapling.
Downloaded blends remain in the ignored source cache, not the shipped map.
"""
import argparse
import hashlib
import json
import subprocess
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
import map_kit as K

UA = {'User-Agent': 'HC1 Forest Base Asset Importer/1.0'}
SOURCE = K.ROOT / 'Sources/ForestBase'
BLENDER = 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
KINDS = {'fir_tree_01': 'fir', 'fir_sapling': 'sapling'}


def fetch(entry, path):
    if path.exists() and hashlib.md5(path.read_bytes()).hexdigest() == entry['md5']:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    data = urllib.request.urlopen(urllib.request.Request(entry['url'], headers=UA), timeout=90).read()
    if hashlib.md5(data).hexdigest() != entry['md5']:
        raise ValueError('Checksum mismatch: ' + entry['url'])
    temporary = path.with_name(path.name + '.download')
    temporary.write_bytes(data)
    temporary.replace(path)


def materials(asset, files, folder, resource):
    names = ('bark', 'trunk_a', 'trunk_b', 'trunk_c', 'twig', 'dead_branches') if asset == 'fir_tree_01' else ('branches', 'twigs')
    jobs, specs = [], {}
    for name in names:
        source = 'bark' if name == 'dead_branches' else name
        resolution = '2k' if source in ('twig', 'twigs') else '1k'
        textures = {}
        for field, prop in (('diff', 'Color'), ('nor_gl', 'Normal'), ('arm', 'ARM')):
            group = files[f'{source}_{field}'][resolution]
            fmt = 'jpg' if 'jpg' in group else 'png'
            filename = f'textures/{source}_{field}_{resolution}.{fmt}'
            jobs.append((group[fmt], folder / filename))
            textures[prop] = filename
        if source in ('twig', 'twigs'):
            textures['Translucency'] = f'textures/{source}_alpha_{resolution}.png'
            jobs.append((files[f'{source}_alpha'][resolution]['png'], folder / textures['Translucency']))
        specs[name] = textures
    # Several branch materials deliberately share the bark scan.
    unique = {str(path): (entry, path) for entry, path in jobs}
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda job: fetch(*job), unique.values()))
    for name, textures in specs.items():
        arm = np.asarray(Image.open(folder / textures['ARM']).convert('RGB'))
        for prop, channel in (('ao', 0), ('rough', 1)):
            Image.fromarray(arm[:, :, channel]).save(folder / f'textures/{name}_{prop}.png')
        lines = ['"Layer0"', '{', ' shader "shaders/complex.shader"', ' F_SPECULAR "1"', ' F_RENDER_BACKFACES "1"', ' TextureMetalness "[0 0 0 0]"']
        for prop in ('Color', 'Normal'):
            lines.append(f' Texture{prop} "{resource}/{textures[prop]}"')
        lines += [f' TextureRoughness "{resource}/textures/{name}_rough.png"', f' TextureAmbientOcclusion "{resource}/textures/{name}_ao.png"']
        if 'Translucency' in textures:
            lines += [' F_ALPHA_TEST "1"', f' TextureTranslucency "{resource}/{textures["Translucency"]}"', ' g_flAlphaTestReference "0.25"']
        K.write_text(folder / f'{asset}_{name}.vmat', '\n'.join(lines + ['}']) + '\n')
    (folder / 'texture-specs.json').write_text(json.dumps(specs, indent=2), encoding='utf-8')
    return names


def modeldocs(asset, folder, resource, names):
    template = (K.ASSETS / 'models/grass/grass_tuft.vmdl').read_text()
    remaps = ',\n'.join(f'{{ from = "{asset}_{name}.vmat" to = "{resource}/{asset}_{name}.vmat" }}' for name in names)
    for variant in 'abc':
        for angle in (0, 90):
            rgba = np.asarray(Image.open(folder / f'impostor_{variant}_{angle}.png').convert('RGBA'))
            # Extrude crown colours into the transparent border, keeping alpha
            # untouched. Mip/bilinear filtering then avoids a black outline.
            color = rgba[:, :, :3].copy()
            transparent = rgba[:, :, 3] < 32
            if transparent.any() and not transparent.all():
                distance, nearest = distance_transform_edt(transparent, return_indices=True)
                border = transparent & (distance <= 12)
                color[border] = color[nearest[0][border], nearest[1][border]]
            Image.fromarray(color).save(folder / f'impostor_{variant}_{angle}_color.png')
            Image.fromarray(rgba[:, :, 3]).save(folder / f'impostor_{variant}_{angle}_alpha.png')
            K.write_text(folder / f'impostor_{variant}_{angle}.vmat', f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_ALPHA_TEST "1"
 F_RENDER_BACKFACES "1"
 TextureColor "{resource}/impostor_{variant}_{angle}_color.png"
 TextureTranslucency "{resource}/impostor_{variant}_{angle}_alpha.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.85 .85 .85 0]"
 TextureMetalness "[0 0 0 0]"
 g_flAlphaTestReference "0.25"
}}
''')
        variant_remaps = remaps + ',\n' + ',\n'.join(f'{{ from = "impostor_{variant}_{angle}.vmat" to = "{resource}/impostor_{variant}_{angle}.vmat" }}' for angle in (0, 90))
        text = template.replace('remaps = [ ] use_global_default = true global_default_material = "models/grass/grass.vmat"', f'remaps = [ {variant_remaps} ] use_global_default = false global_default_material = ""')
        for lod in range(3):
            text = text.replace(f'models/grass/grass_tuft_lod{lod}.obj', f'{resource}/{KINDS[asset]}_{variant}_lod{lod}.obj')
        # Tuned against the compound overview, where whole-crown cards must
        # not replace nearby visible branches. These are ModelDoc thresholds.
        near,far=(350,1400) if asset=='fir_tree_01' else (200,500)
        text = text.replace('switch_threshold = 10.0', f'switch_threshold = {near}.0').replace('switch_threshold = 25.0', f'switch_threshold = {far}.0')
        K.write_text(folder / f'{KINDS[asset]}_{variant}.vmdl', text)
        if asset=='fir_tree_01':
            # Reduced branch geometry remains dimensional in elevated views.
            # Reuse the mesh in every group to make the background cost explicit.
            far_text=text
            for lod in range(3):
                far_text=far_text.replace(f'filename = "{resource}/fir_{variant}_lod{lod}.obj"',f'filename = "{resource}/fir_{variant}_distant.obj"')
            K.write_text(folder / f'fir_{variant}_far.vmdl',far_text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('assets', nargs='*', help='fir_tree_01 and/or fir_sapling; defaults to both')
    parser.add_argument('--finalize', action='store_true', help='Reuse exported geometry and rendered impostors.')
    args = parser.parse_args()
    assets = args.assets or list(KINDS)
    if any(asset not in KINDS for asset in assets):
        parser.error('Supported assets: ' + ', '.join(KINDS))
    for asset in assets:
        SOURCE.mkdir(parents=True, exist_ok=True)
        files = json.load(urllib.request.urlopen(urllib.request.Request('https://api.polyhaven.com/files/' + asset, headers=UA), timeout=30))
        (SOURCE / f'{asset}-files.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
        folder = K.ASSETS / f'models/maps/forestbase/{KINDS[asset]}'
        resource = f'models/maps/forestbase/{KINDS[asset]}'
        folder.mkdir(parents=True, exist_ok=True)
        names = materials(asset, files, folder, resource)
        if not args.finalize:
            fetch(files['blend']['1k']['blend'], SOURCE / f'{asset}.blend')
            subprocess.run([BLENDER, '--background', str(SOURCE / f'{asset}.blend'), '--python', str(Path(__file__).with_name('forestbase_fir_blender.py')), '--', asset], check=True)
            if asset=='fir_tree_01':
                subprocess.run([BLENDER,'--background','--python',str(Path(__file__).with_name('forestbase_distant_fir_blender.py'))],check=True)
        modeldocs(asset, folder, resource, names)
        if asset=='fir_tree_01':
            if not args.finalize or not all((folder/f'fir_{v}_horizon.obj').exists() for v in 'abc'):
                subprocess.run([BLENDER,'--background','--factory-startup','--threads','4','--python',
                    str(Path(__file__).with_name('forestbase_horizon_fir_blender.py')),
                    '--','--output',str(folder)],check=True)
            import forestbase_forest
            forestbase_forest.write_horizon_models(folder)
        (folder / 'LICENSE.txt').write_text(f'{asset} by Rico Cilliers / Rob Tuytel, Poly Haven. CC0 1.0.\nhttps://polyhaven.com/a/{asset}\nhttps://polyhaven.com/license\n', encoding='utf-8')
        print(asset, 'game assets ready', flush=True)


if __name__ == '__main__':
    main()
