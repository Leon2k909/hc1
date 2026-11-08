from pathlib import Path
import requests, gzip, json
root=Path(__file__).resolve().parents[1]/'Sources/Veridant/cairo-lion'
root.mkdir(parents=True,exist_ok=True)
uid='3d1956be9e724235817f03a1d570f408'
info=requests.get('https://api.sketchfab.com/v3/models/'+uid).json()
(root/'source-metadata.json').write_text(json.dumps(info,indent=2))
response=requests.get('https://huggingface.co/datasets/allenai/objaverse/resolve/main/object-paths.json.gz');response.raise_for_status()
paths=json.loads(gzip.decompress(response.content))
(root/'objaverse-paths.json').write_text(json.dumps({k:paths.get(k) for k in [uid,'e7e957b26c4b480ab2daf47fe93beede']}))
path=paths[uid]
response=requests.get('https://huggingface.co/datasets/allenai/objaverse/resolve/main/'+path);response.raise_for_status()
(root/'lion.glb').write_bytes(response.content)
print(path, len(response.content), info.get('license'))
