from pathlib import Path
import json,hashlib
from native import ROOT,OUT
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((OUT/'manifest.json').read_text());assert json.loads((OUT/'validation.json').read_text())['actual_play_mode_checked']
source=ROOT/m['source'];assert sha(source)==m['source_sha256']
stage=OUT/'install-stage/Assets/models/maps/riverdale';stage.mkdir(parents=True,exist_ok=True)
t=(ROOT/'Assets/models/maps/riverdale/shared-reel-v1/yard_without_reel.obj').read_text().replace('mtllib yard_without_reel.mtl','mtllib riverdale_yard_props.mtl');(stage/source.name).write_text(t)
scene='scenes/maps/Riverdale/riverdale.scene'
manifest=dict(sceneRelative=scene,sceneSHA256=sha(ROOT/'Assets'/scene),resource=m['reused_resource'],files=[dict(phase='map',relative='models/maps/riverdale/'+source.name,before=sha(source),after=sha(stage/source.name))])
(OUT/'install-manifest.json').write_text(json.dumps(manifest,indent=2))
s=(ROOT/'Sources/Orion/cable-reel-trial-v1/install_map.cs.txt').read_text().replace('output/orion-cable-reel-installed-20261030','output/riverdale/shared-reel-v1').replace('"manifest.json"','"install-manifest.json"').replace('output,"stage/Assets"','output,"install-stage/Assets"').replace('ORION cable reel','Riverdale north-lane cable reel').replace('Orion','Riverdale').replace('scenes/maps/orion/orion.scene','scenes/maps/riverdale/riverdale.scene').replace('Sources/Orion/cable-reel-trial-v1/native-instance.json','Sources/Riverdale/shared-reel-v1/native-instance.json')
s=s.replace('go.WorldPosition=new Vector3(1320,-380,240);','go.WorldScale=new Vector3(.847457627f,.935064935f,.847457627f);go.WorldPosition=new Vector3(3803.050847458f,1696.051948052f,-.254237288f);')
s=s.replace('||model.Materials.Count()!=6||model.Materials.Any(m=>m is null||!m.ResourcePath.StartsWith("materials/orion/cable_reel_v1/"))','')
s=s.replace('RemovedPlaceholderTriangles=56,RemovedStairCollider=true','RemovedPlaceholderTriangles=300,CollisionUnchanged=true')
(Path(__file__).parent/'install.cs.txt').write_text(s)
print('Prepared guarded installation')
