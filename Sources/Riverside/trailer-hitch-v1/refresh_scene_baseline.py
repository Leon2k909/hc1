"""Record the inspected concurrent store-light edit; never writes the public scene."""
from pathlib import Path
import json,hashlib
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/trailer-hitch-v1'
scene=ROOT/'Assets/scenes/maps/Riverside/riverside.scene';data=scene.read_bytes();current=json.loads(data)
original=json.loads((ROOT/'output/riverside/tv-aerial-v1/install-before/riverside.scene').read_text())
group=next(g for g in current['GameObjects'] if g.get('Name')=='Roof TV Aerials')
assert len(group['Children'])==1 and group['Children'][0]['Name']=='T2 Rooftop TV Aerial'
comparable=json.loads(data);comparable['GameObjects']=[g for g in comparable['GameObjects'] if g['__guid']!=group['__guid']]
lights=next(g for g in comparable['GameObjects'] if g.get('Name')=='Lights')
beforelights=next(g for g in original['GameObjects'] if g.get('Name')=='Lights')
light=lights['Children'][70];assert light['__guid']==beforelights['Children'][70]['__guid']
assert beforelights['Children'][70]['Components'][0]['Intensity']==1 and light['Components'][0]['Intensity']==.2
light['Components'][0]['Intensity']=1
assert comparable==original,'Another concurrent edit requires inspection.'
manifest=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
key=scene.relative_to(ROOT).as_posix()
for p,h in manifest['protected'].items():
    if p!=key:assert sha(ROOT/p)==h,'Public model source changed.'
oldhash=manifest['protected'][key];manifest['protected'][key]=hashlib.sha256(data).hexdigest()
(OUT/'review-scene-baseline.scene').write_bytes(data)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
receipt=dict(PublicSceneWritten=False,InspectedConcurrentEdit=dict(Light=light['Name'],Property='Intensity',Before=1,After=.2),PreviousHash=oldhash,CurrentHash=manifest['protected'][key])
(OUT/'scene-baseline-refresh.json').write_text(json.dumps(receipt,indent=2));print(json.dumps(receipt,indent=2))
