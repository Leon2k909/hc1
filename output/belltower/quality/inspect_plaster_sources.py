"""Inspect original small Poly Haven albedo maps; no pixel edits."""
from pathlib import Path
import hashlib
import json
import urllib.request

destination=Path(__file__).parent/'plaster-v1-candidates'
destination.mkdir(exist_ok=True)
for ident in ('worn_plaster_wall','plastered_stone_wall','rough_plaster_broken'):
    request=urllib.request.Request(f'https://api.polyhaven.com/files/{ident}',headers={'User-Agent':'BelltowerVisualPass/1.0'})
    with urllib.request.urlopen(request,timeout=30) as response:
        files=json.load(response)
    source=files['Diffuse']['1k']['jpg']
    path=destination/(ident+'.jpg')
    if not path.exists():
        with urllib.request.urlopen(source['url'],timeout=30) as response:
            path.write_bytes(response.read())
    assert hashlib.md5(path.read_bytes()).hexdigest()==source['md5']
    (destination/(ident+'.json')).write_text(json.dumps(source,indent=2)+'\n')
    print(f'{ident}: {path.stat().st_size} bytes; original MD5 verified',flush=True)
