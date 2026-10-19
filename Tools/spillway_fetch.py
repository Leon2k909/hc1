"""Download the map's CC0 material sources into its editor import staging tree."""
from pathlib import Path
import json
import urllib.request

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'output/spillway/stage/materials/spillway/scans'
DEST.mkdir(parents=True, exist_ok=True)
assets = []
for name, author in [('concrete_wall_009', 'Charlotte Baglioni'), ('concrete_layers_02', 'Rob Tuytel'), ('seaside_rock', 'Dimitrios Savva')]:
    files = []
    for kind in ('diff', 'nor_dx', 'rough'):
        filename = f'{name}_{kind}_2k.jpg'
        url = f'https://dl.polyhaven.org/file/ph-assets/Textures/jpg/2k/{name}/{filename}'
        path = DEST / filename
        if not path.exists():
            urllib.request.urlretrieve(url, path)
        files.append({'file': f'materials/spillway/scans/{filename}', 'url': url, 'bytes': path.stat().st_size})
        print(filename, path.stat().st_size, flush=True)
    assets.append({'asset': name, 'author': author, 'license': 'CC0-1.0', 'source': f'https://polyhaven.com/a/{name}', 'files': files})
assets.append({'asset': 'kloofendal_38d_partly_cloudy_puresky', 'authors': ['Greg Zaal', 'Jarod Guest'], 'license': 'CC0-1.0', 'source': 'https://polyhaven.com/a/kloofendal_38d_partly_cloudy_puresky', 'file': 'materials/spillway/sky/clouds.exr'})
sky=DEST.parent/'sky/clouds.exr'
sky.parent.mkdir(parents=True,exist_ok=True)
if not sky.exists():
    urllib.request.urlretrieve('https://dl.polyhaven.org/file/ph-assets/HDRIs/exr/4k/kloofendal_38d_partly_cloudy_puresky_4k.exr',sky)
name='kloppenheim_01_puresky'
clouds=DEST.parent/'sky/overcast.exr'
url=f'https://dl.polyhaven.org/file/ph-assets/HDRIs/exr/4k/{name}_4k.exr'
if not clouds.exists():urllib.request.urlretrieve(url,clouds)
assets.append({'asset':name,'authors':['Greg Zaal','Jarod Guest'],'license':'CC0-1.0',
    'source':f'https://polyhaven.com/a/{name}','file':'materials/spillway/sky/overcast.exr','url':url})
name='kloppenheim_03_puresky'
clouds=DEST.parent/'sky/storm.exr'
url=f'https://dl.polyhaven.org/file/ph-assets/HDRIs/exr/4k/{name}_4k.exr'
if not clouds.exists():urllib.request.urlretrieve(url,clouds)
assets.append({'asset':name,'authors':['Greg Zaal','Jarod Guest'],'license':'CC0-1.0',
    'source':f'https://polyhaven.com/a/{name}','file':'materials/spillway/sky/storm.exr','url':url})
(ROOT / 'Sources/Spillway/material-sources.json').write_text(json.dumps(assets, indent=2))
