"""Download this one CC0 chair's published files and verify their API digests."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parent
data=json.loads((ROOT/'files.json').read_text(encoding='utf-8'))
bundle=data['gltf']['2k']['gltf']
files={'dining_chair_02_2k.gltf':bundle,**bundle['include']}
for kind in ('Diffuse','nor_gl','Rough','AO'):
    row=data[kind]['2k']['png']
    files['textures/'+row['url'].rsplit('/',1)[1]]=row
for relative,row in files.items():
    target=(ROOT/relative).resolve()
    assert target.is_relative_to(ROOT.resolve())
    assert row['url'].startswith('https://dl.polyhaven.org/file/ph-assets/Models/')
    if target.exists():
        content=target.read_bytes()
    else:
        request=urllib.request.Request(row['url'],headers={'User-Agent':'Veridant-local-asset-evaluation/1.0'})
        with urllib.request.urlopen(request,timeout=40) as response: content=response.read()
        assert len(content)==row['size'] and hashlib.md5(content).hexdigest()==row['md5']
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(content)
    assert len(content)==row['size'] and hashlib.md5(content).hexdigest()==row['md5']
    print(relative,flush=True)
(ROOT/'SOURCE.md').write_text(
    '# Dining Chair 02\n\n'
    'Artist: James Ray Cock. Source: https://polyhaven.com/a/dining_chair_02\n\n'
    'License: CC0 1.0, as published at https://polyhaven.com/license .\n'
    'The files.json manifest retains the official download URLs, sizes and MD5 digests.\n'
    'Mesh and original textures are preserved here. Game conversion is a separate local output.\n',encoding='utf-8')
