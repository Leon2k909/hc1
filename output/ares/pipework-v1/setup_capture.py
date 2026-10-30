from pathlib import Path
import hashlib
import json

root=Path(__file__).resolve().parents[3]
original=root/'Sources/Ares/pressure-doors-v2/capture.cs.txt'
target=root/'Sources/Ares/pipework-v1/capture.cs.txt'
assert not target.exists()
source=original.read_text().replace('output/ares/airlock-door-v1','output/ares/pipework-v1')
source=source.replace('Sources/Ares/pressure-doors-v2','Sources/Ares/pipework-v1')
source=source.replace('models/maps/ares/pressure-doors-v2/trial_hall.vmdl','models/maps/ares/pipework-v1/trial_hall.vmdl')
source=source.replace('stage-v3','stage-v1')
target.write_text(source)
config={'directory':'pipework-v1-before','name':'cargo-close','width':1600,'height':1000,
        'position':'-1175,860,255','angles':'0.93,180,0','fov':58,'exposure':2.4,
        'settle_ms':0,'preserve_unsaved':True,
        'expected_scene_sha256':hashlib.sha256((root/'Assets/scenes/maps/Ares/ares.scene').read_bytes()).hexdigest()}
(root/'output/ares/pipework-v1/capture-request.json').write_text(json.dumps(config))
print('Prepared pipework capture')
