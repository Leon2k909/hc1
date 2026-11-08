from pathlib import Path
import hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
OUT=Path(tempfile.gettempdir())/'belltower-well-frame-v2';m=json.loads((OUT/'install-stage/manifest.json').read_text())
def sha(p):
    with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert all(sha(ROOT/p)==r['after'] for p,r in m['files'].items());assert all(sha(ROOT/p)==h for p,h in m['protected'].items());assert all(not (ROOT/p).exists() for p in m['deleted'])
r=json.loads((OUT/'install-stage/installed.json').read_text());r.update(json.loads((OUT/'install-stage/deleted.json').read_text()));(ROOT/'Sources/Belltower/well-frame-v2/installed.json').write_text(json.dumps(r,indent=2))
p=ROOT/'Sources/Belltower/well-frame-v2/build.py';s=p.read_text();a=s.index('old=K.Model()');p.write_text(s[:a]+"print({'accepted_resource_staged':True,'lods':lods})\n")
print(r)
