from pathlib import Path
import json

root = Path(__file__).resolve().parents[3]
source = root / 'Sources/Ares/floor-finish-v4/capture.cs.txt'
capture = source.read_text().replace('output/ares/floor-finish-v4', 'output/ares/floor-live-v4')
capture = capture.replace('var report=new {Written=written,', '''var publicModel=Model.Load("models/maps/ares/ares_hall.vmdl");
var report=new {PublicModelError=publicModel.IsError,PublicMaterials=publicModel.Materials.Select(m=>m.ResourcePath).ToArray(),Written=written,''')
(source.parent / 'capture_live_floor.cs.txt').write_text(capture)
config = json.loads((root / 'output/ares/floor-finish-v4/capture-config.json').read_text())
config['variants'] = [{'name': 'installed'}]
(root / 'output/ares/floor-live-v4/capture-config.json').write_text(json.dumps(config, indent=2))
