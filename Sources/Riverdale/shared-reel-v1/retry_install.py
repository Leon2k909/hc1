import hashlib,json
from native import ROOT,OUT,script
p=json.loads((OUT/'install-manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/'Assets'/p['sceneRelative'])==p['sceneSHA256']
for f in p['files']:assert sha(ROOT/'Assets'/f['relative'])==f['before']
s=ROOT/'Sources/Riverdale/shared-reel-v1/install.cs.txt';t=s.read_text().replace('Copy(target,backup,false)','Copy(target,backup,true)').replace('Copy(scenePath,sceneBackup,false)','Copy(scenePath,sceneBackup,true)');s.write_text(t)
print(json.dumps(script(s),indent=2))
